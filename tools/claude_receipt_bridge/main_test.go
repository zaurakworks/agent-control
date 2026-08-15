package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

const testToken = "0123456789abcdef0123456789abcdef"

func TestEmitHookUsesOnlyBoundIDsAndAllowlistedEvent(t *testing.T) {
	t.Parallel()
	fixedTime := time.Date(2026, 8, 12, 23, 45, 1, 123, time.UTC)
	input := `{
		"session_id":"claude-session-1",
		"hook_event_name":"TaskCompleted",
		"task_id":"provider-task-must-not-leak",
		"task_subject":"sensitive subject",
		"transcript_path":"C:/sensitive/transcript.jsonl",
		"last_assistant_message":"sensitive output"
	}`
	env := map[string]string{
		taskIDEnv:     "task_7491d7cca639",
		dispatchIDEnv: "ctx_b79017455715",
		tokenEnv:      testToken,
	}
	var got receipt
	var gotToken string
	send := func(_ context.Context, r receipt, token string) error {
		got = r
		gotToken = token
		return nil
	}

	emitted, err := emitHook(context.Background(), strings.NewReader(input), envLookup(env), func() time.Time { return fixedTime }, send)
	if err != nil {
		t.Fatalf("emitHook() error = %v", err)
	}
	if !emitted {
		t.Fatal("emitHook() did not emit")
	}
	want := receipt{
		TaskID:     "task_7491d7cca639",
		DispatchID: "ctx_b79017455715",
		Event:      "TaskCompleted",
		Time:       "2026-08-12T23:45:01.000000123Z",
	}
	if got != want {
		t.Fatalf("receipt = %#v, want %#v", got, want)
	}
	if gotToken != testToken {
		t.Fatal("sender did not receive the configured token")
	}

	encoded, err := json.Marshal(got)
	if err != nil {
		t.Fatal(err)
	}
	var fields map[string]any
	if err := json.Unmarshal(encoded, &fields); err != nil {
		t.Fatal(err)
	}
	if len(fields) != 4 {
		t.Fatalf("payload contains %d fields, want exactly 4: %s", len(fields), encoded)
	}
	for _, key := range []string{"taskId", "dispatchId", "event", "time"} {
		if _, ok := fields[key]; !ok {
			t.Fatalf("payload lacks %q: %s", key, encoded)
		}
	}
}

func TestEmitHookAllowsExactlyThreePositiveEvents(t *testing.T) {
	t.Parallel()
	env := map[string]string{taskIDEnv: "task_1", dispatchIDEnv: "dispatch_1", tokenEnv: testToken}
	for _, event := range []string{"UserPromptSubmit", "Stop", "TaskCompleted"} {
		t.Run(event, func(t *testing.T) {
			calls := 0
			input := `{"session_id":"session-1","hook_event_name":"` + event + `"}`
			emitted, err := emitHook(context.Background(), strings.NewReader(input), envLookup(env), time.Now, func(_ context.Context, _ receipt, _ string) error {
				calls++
				return nil
			})
			if err != nil || !emitted || calls != 1 {
				t.Fatalf("event %s: emitted=%v calls=%d err=%v", event, emitted, calls, err)
			}
		})
	}

	for _, event := range []string{"StopFailure", "SessionEnd", "PreToolUse", ""} {
		t.Run("reject_"+event, func(t *testing.T) {
			calls := 0
			input := `{"session_id":"session-1","hook_event_name":"` + event + `"}`
			emitted, err := emitHook(context.Background(), strings.NewReader(input), envLookup(env), time.Now, func(_ context.Context, _ receipt, _ string) error {
				calls++
				return nil
			})
			if err != nil || emitted || calls != 0 {
				t.Fatalf("event %s: emitted=%v calls=%d err=%v", event, emitted, calls, err)
			}
		})
	}
}

func TestEmitHookFailsClosedAtAdapterBoundaryButRunRemainsNonBlocking(t *testing.T) {
	t.Parallel()
	tests := []struct {
		name  string
		input string
		env   map[string]string
	}{
		{name: "malformed JSON", input: `{`, env: validEnv()},
		{name: "missing session", input: `{"hook_event_name":"Stop"}`, env: validEnv()},
		{name: "invalid task", input: validHookInput("Stop"), env: map[string]string{taskIDEnv: "../task", dispatchIDEnv: "dispatch_1", tokenEnv: testToken}},
		{name: "missing dispatch", input: validHookInput("Stop"), env: map[string]string{taskIDEnv: "task_1", tokenEnv: testToken}},
		{name: "short token", input: validHookInput("Stop"), env: map[string]string{taskIDEnv: "task_1", dispatchIDEnv: "dispatch_1", tokenEnv: "short"}},
		{name: "extra JSON", input: validHookInput("Stop") + `{}`, env: validEnv()},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			called := false
			emitted, err := emitHook(context.Background(), strings.NewReader(test.input), envLookup(test.env), time.Now, func(_ context.Context, _ receipt, _ string) error {
				called = true
				return nil
			})
			if err == nil || emitted || called {
				t.Fatalf("emitted=%v called=%v err=%v", emitted, called, err)
			}

			var stdout, stderr bytes.Buffer
			exitCode := run([]string{"hook"}, strings.NewReader(test.input), &stdout, &stderr, envLookup(test.env))
			if exitCode != 0 {
				t.Fatalf("hook mode exit code = %d, want observational exit 0", exitCode)
			}
			if stdout.Len() != 0 {
				t.Fatalf("hook mode wrote stdout: %q", stdout.String())
			}
		})
	}
}

func TestHookInputLimit(t *testing.T) {
	t.Parallel()
	input := strings.Repeat("x", maxHookInputBytes+1)
	_, err := emitHook(context.Background(), strings.NewReader(input), envLookup(validEnv()), time.Now, func(context.Context, receipt, string) error { return nil })
	if err == nil || !strings.Contains(err.Error(), "exceeds") {
		t.Fatalf("error = %v, want size error", err)
	}
}

func TestReceiptHandlerAcceptsMinimalAuthenticatedPayload(t *testing.T) {
	t.Parallel()
	var output bytes.Buffer
	handler := newReceiptHandler(testToken, &output)
	payload := `{"taskId":"task_1","dispatchId":"dispatch_1","event":"Stop","time":"2026-08-12T23:45:01Z"}`
	req := httptest.NewRequest(http.MethodPost, receiptPath, strings.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(tokenHeader, testToken)
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, req)
	if response.Code != http.StatusNoContent {
		t.Fatalf("status = %d, body=%q", response.Code, response.Body.String())
	}
	if output.String() != payload+"\n" {
		t.Fatalf("JSONL output = %q, want %q", output.String(), payload+"\n")
	}
}

func TestReceiptHandlerRejectsInvalidRequests(t *testing.T) {
	t.Parallel()
	valid := `{"taskId":"task_1","dispatchId":"dispatch_1","event":"Stop","time":"2026-08-12T23:45:01Z"}`
	tests := []struct {
		name        string
		method      string
		path        string
		contentType string
		token       string
		body        string
		status      int
	}{
		{name: "wrong path", method: http.MethodPost, path: "/other", contentType: "application/json", token: testToken, body: valid, status: http.StatusNotFound},
		{name: "wrong method", method: http.MethodGet, path: receiptPath, contentType: "application/json", token: testToken, body: valid, status: http.StatusMethodNotAllowed},
		{name: "wrong token", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: strings.Repeat("x", len(testToken)), body: valid, status: http.StatusUnauthorized},
		{name: "wrong content type", method: http.MethodPost, path: receiptPath, contentType: "text/plain", token: testToken, body: valid, status: http.StatusUnsupportedMediaType},
		{name: "unknown field", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: testToken, body: strings.TrimSuffix(valid, "}") + `,"sessionId":"leak"}`, status: http.StatusBadRequest},
		{name: "unknown event", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: testToken, body: strings.Replace(valid, `"Stop"`, `"StopFailure"`, 1), status: http.StatusBadRequest},
		{name: "non UTC time", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: testToken, body: strings.Replace(valid, `2026-08-12T23:45:01Z`, `2026-08-12T19:45:01-04:00`, 1), status: http.StatusBadRequest},
		{name: "multiple values", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: testToken, body: valid + `{}`, status: http.StatusBadRequest},
		{name: "oversized", method: http.MethodPost, path: receiptPath, contentType: "application/json", token: testToken, body: strings.Repeat("x", maxReceiptBodyBytes+1), status: http.StatusBadRequest},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var output bytes.Buffer
			handler := newReceiptHandler(testToken, &output)
			req := httptest.NewRequest(test.method, test.path, strings.NewReader(test.body))
			req.Header.Set("Content-Type", test.contentType)
			req.Header.Set(tokenHeader, test.token)
			response := httptest.NewRecorder()
			handler.ServeHTTP(response, req)
			if response.Code != test.status {
				t.Fatalf("status = %d, want %d; body=%q", response.Code, test.status, response.Body.String())
			}
			if output.Len() != 0 {
				t.Fatalf("invalid request reached sink: %q", output.String())
			}
		})
	}
}

func TestWakeAggregatorAggregatesAndDeduplicatesForTTL(t *testing.T) {
	t.Parallel()
	start := time.Date(2026, 8, 13, 6, 30, 0, 0, time.UTC)
	state := newWakeAggregator(2 * time.Minute)

	ignored := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "UserPromptSubmit", Time: start.Format(time.RFC3339Nano)}
	if state.add(ignored, start) {
		t.Fatal("UserPromptSubmit must not create a completion wake")
	}

	stop := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "Stop", Time: start.Add(time.Second).Format(time.RFC3339Nano)}
	taskCompleted := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "TaskCompleted", Time: start.Add(2 * time.Second).Format(time.RFC3339Nano)}
	otherStop := receipt{TaskID: "task_2", DispatchID: "ctx_2", Event: "Stop", Time: start.Add(3 * time.Second).Format(time.RFC3339Nano)}
	for _, item := range []receipt{otherStop, stop, taskCompleted} {
		if !state.add(item, start.Add(4*time.Second)) {
			t.Fatalf("first receipt was rejected: %#v", item)
		}
	}
	if state.add(stop, start.Add(5*time.Second)) {
		t.Fatal("duplicate receipt entered the pending aggregate")
	}
	if got := state.pendingCount(); got != 3 {
		t.Fatalf("pendingCount() = %d, want 3", got)
	}

	batch := state.takePending()
	if len(batch) != 3 {
		t.Fatalf("batch length = %d, want 3", len(batch))
	}
	if batch[0].TaskID != "task_1" || batch[0].Event != "Stop" || batch[1].Event != "TaskCompleted" || batch[2].TaskID != "task_2" {
		t.Fatalf("batch is not deterministically sorted: %#v", batch)
	}
	state.markPublished(batch, start.Add(6*time.Second))
	if state.add(stop, start.Add(time.Minute)) {
		t.Fatal("published duplicate bypassed the TTL")
	}
	if !state.add(stop, start.Add(2*time.Minute+6*time.Second)) {
		t.Fatal("receipt did not become eligible when its TTL expired")
	}
}

func TestWakeAggregatorDoesNotDeduplicateFailedPublication(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 8, 13, 6, 30, 0, 0, time.UTC)
	state := newWakeAggregator(2 * time.Minute)
	item := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "Stop", Time: now.Format(time.RFC3339Nano)}
	if !state.add(item, now) {
		t.Fatal("first receipt was rejected")
	}
	if got := state.takePending(); len(got) != 1 {
		t.Fatalf("batch length = %d, want 1", len(got))
	}
	if !state.add(item, now.Add(time.Second)) {
		t.Fatal("a receipt without a successful publication was incorrectly deduplicated")
	}
}

func TestRunWakeAggregatorPublishesOneSignalForOneWindow(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	incoming := make(chan receipt, 4)
	published := make(chan []receipt, 2)
	done := make(chan struct{})
	go func() {
		defer close(done)
		runWakeAggregator(ctx, incoming, func(_ context.Context, batch []receipt, _ time.Time) (string, error) {
			published <- append([]receipt(nil), batch...)
			return "msg_window_1", nil
		}, io.Discard)
	}()
	t.Cleanup(func() {
		cancel()
		<-done
	})

	now := time.Now().UTC()
	stop := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "Stop", Time: now.Format(time.RFC3339Nano)}
	completed := receipt{TaskID: "task_1", DispatchID: "ctx_1", Event: "TaskCompleted", Time: now.Add(time.Millisecond).Format(time.RFC3339Nano)}
	incoming <- stop
	incoming <- stop
	incoming <- completed

	select {
	case batch := <-published:
		if len(batch) != 2 {
			t.Fatalf("published batch length = %d, want 2", len(batch))
		}
	case <-time.After(2 * time.Second):
		t.Fatal("wake aggregate was not published within two seconds")
	}

	incoming <- stop
	select {
	case duplicate := <-published:
		t.Fatalf("duplicate produced a second wake signal: %#v", duplicate)
	case <-time.After(2 * wakeAggregateWindow):
	}
}

func TestPublishWakeSendsOneMachineReadableStatus(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 8, 13, 6, 30, 10, 0, time.UTC)
	batch := []receipt{
		{TaskID: "task_1", DispatchID: "ctx_1", Event: "Stop", Time: now.Add(-2 * time.Second).Format(time.RFC3339Nano)},
		{TaskID: "task_1", DispatchID: "ctx_1", Event: "TaskCompleted", Time: now.Add(-time.Second).Format(time.RFC3339Nano)},
	}
	var command string
	var args []string
	runner := func(_ context.Context, name string, commandArgs ...string) ([]byte, error) {
		command = name
		args = append([]string(nil), commandArgs...)
		return []byte(`{"ok":true,"result":{"message":{"id":"msg_wake_1","run_id":"run_1","type":"status"}}}`), nil
	}

	messageID, err := publishWake(context.Background(), "run_1", batch, now, "orca-test", runner)
	if err != nil {
		t.Fatalf("publishWake() error = %v", err)
	}
	if messageID != "msg_wake_1" || command != "orca-test" {
		t.Fatalf("message=%q command=%q", messageID, command)
	}
	if value := commandArgValue(args, "--to"); value != "run:run_1" {
		t.Fatalf("--to = %q", value)
	}
	if value := commandArgValue(args, "--type"); value != "status" {
		t.Fatalf("--type = %q", value)
	}
	var payload wakeEnvelope
	if err := json.Unmarshal([]byte(commandArgValue(args, "--payload")), &payload); err != nil {
		t.Fatalf("decode payload: %v", err)
	}
	if payload.Schema != wakeSchema || payload.Version != 1 || payload.RunID != "run_1" || payload.ReceiptCount != 2 || payload.DispatchCount != 1 || len(payload.Receipts) != 2 {
		t.Fatalf("unexpected wake payload: %#v", payload)
	}
	if payload.FirstEventAt != batch[0].Time || payload.LastEventAt != batch[1].Time || payload.ObservedAt != now.Format(time.RFC3339Nano) {
		t.Fatalf("unexpected wake timeline: %#v", payload)
	}
}

func TestPublishWakeRejectsNonCompletionAndMismatchedOrcaReceipt(t *testing.T) {
	t.Parallel()
	now := time.Date(2026, 8, 13, 6, 30, 10, 0, time.UTC)
	invalid := []receipt{{TaskID: "task_1", DispatchID: "ctx_1", Event: "UserPromptSubmit", Time: now.Format(time.RFC3339Nano)}}
	called := false
	if _, err := publishWake(context.Background(), "run_1", invalid, now, "orca", func(context.Context, string, ...string) ([]byte, error) {
		called = true
		return nil, nil
	}); err == nil || called {
		t.Fatalf("invalid event reached Orca: called=%v err=%v", called, err)
	}

	valid := []receipt{{TaskID: "task_1", DispatchID: "ctx_1", Event: "Stop", Time: now.Format(time.RFC3339Nano)}}
	_, err := publishWake(context.Background(), "run_1", valid, now, "orca", func(context.Context, string, ...string) ([]byte, error) {
		return []byte(`{"ok":true,"result":{"message":{"id":"msg_wrong","run_id":"run_other","type":"status"}}}`), nil
	})
	if err == nil || !strings.Contains(err.Error(), "mismatch") {
		t.Fatalf("mismatched Orca receipt error = %v", err)
	}
}

func TestWakeModeRequiresExplicitRun(t *testing.T) {
	t.Parallel()
	var stdout, stderr bytes.Buffer
	code := run([]string{"wake"}, strings.NewReader(""), &stdout, &stderr, envLookup(map[string]string{tokenEnv: testToken}))
	if code != 2 || stdout.Len() != 0 || !strings.Contains(stderr.String(), wakeRunIDEnv) {
		t.Fatalf("code=%d stdout=%q stderr=%q", code, stdout.String(), stderr.String())
	}
}

func TestFixedEndpointIsLiteralLoopback(t *testing.T) {
	t.Parallel()
	parsed, err := url.Parse(receiptURL)
	if err != nil || parsed.Scheme != "http" || parsed.Host != listenAddress || parsed.Path != receiptPath || parsed.Hostname() != "127.0.0.1" {
		t.Fatalf("receipt endpoint is not a fixed literal loopback address: %s", receiptURL)
	}
}

func TestRunRejectsArbitraryModes(t *testing.T) {
	t.Parallel()
	for _, args := range [][]string{nil, {"hook", "http://example.com"}, {"shell"}} {
		var stdout, stderr bytes.Buffer
		if code := run(args, strings.NewReader(""), &stdout, &stderr, envLookup(validEnv())); code != 2 {
			t.Fatalf("args=%v exit code=%d, want 2", args, code)
		}
	}
}

func TestBuiltBinaryEndToEnd(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping subprocess validation in short mode")
	}

	executableName := "claude-receipt-bridge"
	if runtime.GOOS == "windows" {
		executableName += ".exe"
	}
	executable := filepath.Join(t.TempDir(), executableName)
	build := exec.Command("go", "build", "-trimpath", "-o", executable, ".")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build binary: %v\n%s", err, output)
	}

	listener := exec.Command(executable, "listen")
	listener.Env = replaceEnv(os.Environ(), map[string]string{tokenEnv: testToken})
	listenerStdout, err := listener.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	listenerStderr, err := listener.StderrPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := listener.Start(); err != nil {
		t.Fatalf("start listener: %v", err)
	}
	t.Cleanup(func() {
		if listener.Process != nil {
			_ = listener.Process.Kill()
			_, _ = listener.Process.Wait()
		}
	})

	bannerResult := make(chan string, 1)
	go func() {
		scanner := bufio.NewScanner(listenerStderr)
		if scanner.Scan() {
			bannerResult <- scanner.Text()
			return
		}
		bannerResult <- ""
	}()
	select {
	case banner := <-bannerResult:
		if !strings.Contains(banner, listenAddress+receiptPath) {
			t.Fatalf("listener did not announce fixed endpoint: %q", banner)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("listener did not start within 3 seconds")
	}

	receiptResult := make(chan string, 1)
	go func() {
		scanner := bufio.NewScanner(listenerStdout)
		if scanner.Scan() {
			receiptResult <- scanner.Text()
			return
		}
		receiptResult <- ""
	}()

	hook := exec.Command(executable, "hook")
	hook.Env = replaceEnv(os.Environ(), map[string]string{
		tokenEnv:      testToken,
		taskIDEnv:     "task_7491d7cca639",
		dispatchIDEnv: "ctx_b79017455715",
	})
	hook.Stdin = strings.NewReader(`{
		"session_id":"validation-session",
		"hook_event_name":"Stop",
		"transcript_path":"C:/must-not-leak.jsonl",
		"last_assistant_message":"must-not-leak"
	}`)
	started := time.Now()
	hookOutput, err := hook.CombinedOutput()
	elapsed := time.Since(started)
	if err != nil {
		t.Fatalf("hook process: %v\n%s", err, hookOutput)
	}
	if len(hookOutput) != 0 {
		t.Fatalf("hook process wrote output: %q", hookOutput)
	}
	if elapsed > 2*time.Second {
		t.Fatalf("local hook path took %s, want <=2s including process startup", elapsed)
	}

	select {
	case line := <-receiptResult:
		var fields map[string]any
		if err := json.Unmarshal([]byte(line), &fields); err != nil {
			t.Fatalf("listener output is not JSON: %q: %v", line, err)
		}
		if len(fields) != 4 || fields["taskId"] != "task_7491d7cca639" || fields["dispatchId"] != "ctx_b79017455715" || fields["event"] != "Stop" {
			t.Fatalf("unexpected receipt: %s", line)
		}
		if strings.Contains(line, "must-not-leak") || strings.Contains(line, "transcript") || strings.Contains(line, "session") {
			t.Fatalf("receipt leaked hook input: %s", line)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("listener did not emit a receipt within 3 seconds")
	}
}

func envLookup(values map[string]string) func(string) string {
	return func(key string) string { return values[key] }
}

func validEnv() map[string]string {
	return map[string]string{taskIDEnv: "task_1", dispatchIDEnv: "dispatch_1", tokenEnv: testToken}
}

func validHookInput(event string) string {
	return `{"session_id":"session-1","hook_event_name":"` + event + `"}`
}

func replaceEnv(current []string, replacements map[string]string) []string {
	result := make([]string, 0, len(current)+len(replacements))
	for _, entry := range current {
		key, _, ok := strings.Cut(entry, "=")
		if ok {
			if _, replace := replacements[key]; replace {
				continue
			}
		}
		result = append(result, entry)
	}
	for key, value := range replacements {
		result = append(result, key+"="+value)
	}
	return result
}

func commandArgValue(args []string, name string) string {
	for index := 0; index+1 < len(args); index++ {
		if args[index] == name {
			return args[index+1]
		}
	}
	return ""
}

func TestSynchronizedSinkHandlesWriteFailure(t *testing.T) {
	t.Parallel()
	handler := newReceiptHandler(testToken, errorWriter{})
	payload := `{"taskId":"task_1","dispatchId":"dispatch_1","event":"Stop","time":"2026-08-12T23:45:01Z"}`
	req := httptest.NewRequest(http.MethodPost, receiptPath, strings.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(tokenHeader, testToken)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, req)
	if response.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want %d", response.Code, http.StatusInternalServerError)
	}
}

type errorWriter struct{}

func (errorWriter) Write([]byte) (int, error) { return 0, io.ErrClosedPipe }
