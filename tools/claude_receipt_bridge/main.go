package main

import (
	"bytes"
	"context"
	"crypto/subtle"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"mime"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"
)

const (
	listenAddress       = "127.0.0.1:43127"
	receiptPath         = "/v1/claude-receipts"
	receiptURL          = "http://" + listenAddress + receiptPath
	tokenHeader         = "X-Agent-Control-Receipt-Token"
	tokenEnv            = "AGENT_CONTROL_RECEIPT_TOKEN"
	taskIDEnv           = "AGENT_CONTROL_TASK_ID"
	dispatchIDEnv       = "AGENT_CONTROL_DISPATCH_ID"
	wakeRunIDEnv        = "AGENT_CONTROL_WAKE_RUN_ID"
	maxHookInputBytes   = 1 << 20
	maxReceiptBodyBytes = 4096
	requestTimeout      = 500 * time.Millisecond
	wakeAggregateWindow = 250 * time.Millisecond
	wakeDedupTTL        = 2 * time.Minute
	wakePublishTimeout  = 5 * time.Second
	wakeQueueSize       = 256
	wakeMaxBatch        = 128
	wakeSchema          = "agent-control.claude-receipt-wake"
)

var (
	allowedEvents = map[string]struct{}{
		"UserPromptSubmit": {},
		"Stop":             {},
		"TaskCompleted":    {},
	}
	idPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`)
)

type hookInput struct {
	SessionID     string `json:"session_id"`
	HookEventName string `json:"hook_event_name"`
}

type receipt struct {
	TaskID     string `json:"taskId"`
	DispatchID string `json:"dispatchId"`
	Event      string `json:"event"`
	Time       string `json:"time"`
}

type receiptSender func(context.Context, receipt, string) error

type commandRunner func(context.Context, string, ...string) ([]byte, error)

type wakeEnvelope struct {
	Schema        string    `json:"schema"`
	Version       int       `json:"version"`
	RunID         string    `json:"runId"`
	ReceiptCount  int       `json:"receiptCount"`
	DispatchCount int       `json:"dispatchCount"`
	FirstEventAt  string    `json:"firstEventAt"`
	LastEventAt   string    `json:"lastEventAt"`
	ObservedAt    string    `json:"observedAt"`
	Receipts      []receipt `json:"receipts"`
}

type wakeKey struct {
	TaskID     string
	DispatchID string
	Event      string
}

type wakeAggregator struct {
	ttl     time.Duration
	seen    map[wakeKey]time.Time
	pending map[wakeKey]receipt
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr, os.Getenv))
}

func run(args []string, stdin io.Reader, stdout, stderr io.Writer, getenv func(string) string) int {
	if len(args) != 1 {
		fmt.Fprintln(stderr, "usage: claude-receipt-bridge <hook|listen|wake>")
		return 2
	}

	switch args[0] {
	case "hook":
		ctx, cancel := context.WithTimeout(context.Background(), requestTimeout)
		defer cancel()

		_, err := emitHook(ctx, stdin, getenv, time.Now, sendReceipt)
		if err != nil {
			// Receipt delivery is observational. It must never block or alter Claude's turn.
			fmt.Fprintf(stderr, "claude receipt not emitted: %v\n", err)
		}
		return 0
	case "listen":
		token, err := readToken(getenv)
		if err != nil {
			fmt.Fprintf(stderr, "listener refused to start: %v\n", err)
			return 2
		}
		if err := listen(token, stdout, stderr); err != nil {
			fmt.Fprintf(stderr, "listener stopped: %v\n", err)
			return 1
		}
		return 0
	case "wake":
		token, err := readToken(getenv)
		if err != nil {
			fmt.Fprintf(stderr, "wake listener refused to start: %v\n", err)
			return 2
		}
		runID, err := readWakeRunID(getenv)
		if err != nil {
			fmt.Fprintf(stderr, "wake listener refused to start: %v\n", err)
			return 2
		}
		if err := wake(token, runID, stderr, getenv); err != nil {
			fmt.Fprintf(stderr, "wake listener stopped: %v\n", err)
			return 1
		}
		return 0
	default:
		fmt.Fprintln(stderr, "usage: claude-receipt-bridge <hook|listen|wake>")
		return 2
	}
}

func emitHook(
	ctx context.Context,
	input io.Reader,
	getenv func(string) string,
	now func() time.Time,
	send receiptSender,
) (bool, error) {
	raw, err := io.ReadAll(io.LimitReader(input, maxHookInputBytes+1))
	if err != nil {
		return false, fmt.Errorf("read hook input: %w", err)
	}
	if len(raw) > maxHookInputBytes {
		return false, fmt.Errorf("hook input exceeds %d bytes", maxHookInputBytes)
	}

	var event hookInput
	if err := decodeOneJSON(raw, &event, false); err != nil {
		return false, fmt.Errorf("decode hook input: %w", err)
	}
	if _, ok := allowedEvents[event.HookEventName]; !ok {
		return false, nil
	}
	if strings.TrimSpace(event.SessionID) == "" || len(event.SessionID) > 256 {
		return false, errors.New("allowed event lacks a bounded session_id")
	}

	taskID := getenv(taskIDEnv)
	dispatchID := getenv(dispatchIDEnv)
	if err := validateID("taskId", taskID); err != nil {
		return false, err
	}
	if err := validateID("dispatchId", dispatchID); err != nil {
		return false, err
	}
	token, err := readToken(getenv)
	if err != nil {
		return false, err
	}

	r := receipt{
		TaskID:     taskID,
		DispatchID: dispatchID,
		Event:      event.HookEventName,
		Time:       now().UTC().Format(time.RFC3339Nano),
	}
	if err := send(ctx, r, token); err != nil {
		return false, fmt.Errorf("deliver to fixed loopback endpoint: %w", err)
	}
	return true, nil
}

func sendReceipt(ctx context.Context, r receipt, token string) error {
	body, err := json.Marshal(r)
	if err != nil {
		return fmt.Errorf("encode receipt: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, receiptURL, bytes.NewReader(body))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set(tokenHeader, token)

	dialer := &net.Dialer{Timeout: requestTimeout}
	transport := &http.Transport{
		Proxy:             nil,
		DisableKeepAlives: true,
		DialContext: func(ctx context.Context, network, address string) (net.Conn, error) {
			if network != "tcp" || address != listenAddress {
				return nil, fmt.Errorf("refusing non-fixed endpoint %s/%s", network, address)
			}
			return dialer.DialContext(ctx, "tcp", listenAddress)
		},
	}
	defer transport.CloseIdleConnections()

	client := &http.Client{
		Transport: transport,
		Timeout:   requestTimeout,
		CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	_, _ = io.CopyN(io.Discard, resp.Body, 4096)
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("endpoint returned HTTP %d", resp.StatusCode)
	}
	return nil
}

func listen(token string, stdout, stderr io.Writer) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	fmt.Fprintf(stderr, "listening on http://%s%s\n", listenAddress, receiptPath)
	return serveReceipts(ctx, newReceiptHandler(token, stdout), stderr)
}

func serveReceipts(ctx context.Context, handler http.Handler, stderr io.Writer) error {
	listener, err := net.Listen("tcp", listenAddress)
	if err != nil {
		return err
	}
	defer listener.Close()

	server := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: time.Second,
		ReadTimeout:       time.Second,
		WriteTimeout:      time.Second,
		IdleTimeout:       5 * time.Second,
		MaxHeaderBytes:    8 << 10,
		ErrorLog:          log.New(stderr, "claude-receipt-listener: ", 0),
	}

	done := make(chan struct{})
	go func() {
		select {
		case <-ctx.Done():
			shutdownCtx, cancel := context.WithTimeout(context.Background(), time.Second)
			defer cancel()
			_ = server.Shutdown(shutdownCtx)
		case <-done:
		}
	}()

	err = server.Serve(listener)
	close(done)
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}

func wake(token, runID string, stderr io.Writer, getenv func(string) string) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	receipts := make(chan receipt, wakeQueueSize)
	handler := newReceiptSinkHandler(token, func(item receipt) error {
		if !isWakeEvent(item.Event) {
			return nil
		}
		select {
		case receipts <- item:
			return nil
		default:
			return errors.New("wake receipt queue is full")
		}
	})

	aggregatorDone := make(chan struct{})
	publisher := func(publishCtx context.Context, batch []receipt, observedAt time.Time) (string, error) {
		return publishWake(publishCtx, runID, batch, observedAt, resolveOrcaCLI(getenv), execCommand)
	}
	go func() {
		defer close(aggregatorDone)
		runWakeAggregator(ctx, receipts, publisher, stderr)
	}()

	fmt.Fprintf(
		stderr,
		"wake listener on http://%s%s for %s (aggregate=%s dedup-ttl=%s)\n",
		listenAddress,
		receiptPath,
		runID,
		wakeAggregateWindow,
		wakeDedupTTL,
	)
	err := serveReceipts(ctx, handler, stderr)
	stop()
	<-aggregatorDone
	return err
}

func runWakeAggregator(
	ctx context.Context,
	incoming <-chan receipt,
	publish func(context.Context, []receipt, time.Time) (string, error),
	stderr io.Writer,
) {
	state := newWakeAggregator(wakeDedupTTL)
	var timer *time.Timer
	var timerC <-chan time.Time

	stopTimer := func() {
		if timer == nil {
			return
		}
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
		timer = nil
		timerC = nil
	}
	flush := func(observedAt time.Time) {
		batch := state.takePending()
		if len(batch) == 0 {
			return
		}
		publishCtx, cancel := context.WithTimeout(context.Background(), wakePublishTimeout)
		messageID, err := publish(publishCtx, batch, observedAt)
		cancel()
		if err != nil {
			fmt.Fprintf(stderr, "wake signal failed for %d receipt(s): %v\n", len(batch), err)
			return
		}
		state.markPublished(batch, observedAt)
		fmt.Fprintf(stderr, "wake signal %s published for %d receipt(s)\n", messageID, len(batch))
	}

	for {
		select {
		case <-ctx.Done():
			stopTimer()
			flush(time.Now().UTC())
			return
		case item, ok := <-incoming:
			if !ok {
				stopTimer()
				flush(time.Now().UTC())
				return
			}
			now := time.Now().UTC()
			if !state.add(item, now) {
				continue
			}
			if state.pendingCount() >= wakeMaxBatch {
				stopTimer()
				flush(now)
				continue
			}
			if timerC == nil {
				timer = time.NewTimer(wakeAggregateWindow)
				timerC = timer.C
			}
		case firedAt := <-timerC:
			stopTimer()
			flush(firedAt.UTC())
		}
	}
}

func newWakeAggregator(ttl time.Duration) *wakeAggregator {
	return &wakeAggregator{
		ttl:     ttl,
		seen:    make(map[wakeKey]time.Time),
		pending: make(map[wakeKey]receipt),
	}
}

func (a *wakeAggregator) add(item receipt, observedAt time.Time) bool {
	if !isWakeEvent(item.Event) {
		return false
	}
	a.prune(observedAt)
	key := wakeKey{TaskID: item.TaskID, DispatchID: item.DispatchID, Event: item.Event}
	if _, ok := a.pending[key]; ok {
		return false
	}
	if publishedAt, ok := a.seen[key]; ok && observedAt.Sub(publishedAt) < a.ttl {
		return false
	}
	a.pending[key] = item
	return true
}

func (a *wakeAggregator) prune(now time.Time) {
	for key, publishedAt := range a.seen {
		if now.Sub(publishedAt) >= a.ttl {
			delete(a.seen, key)
		}
	}
}

func (a *wakeAggregator) takePending() []receipt {
	batch := make([]receipt, 0, len(a.pending))
	for key, item := range a.pending {
		batch = append(batch, item)
		delete(a.pending, key)
	}
	sort.Slice(batch, func(i, j int) bool {
		left, right := batch[i], batch[j]
		if left.TaskID != right.TaskID {
			return left.TaskID < right.TaskID
		}
		if left.DispatchID != right.DispatchID {
			return left.DispatchID < right.DispatchID
		}
		if left.Event != right.Event {
			return left.Event < right.Event
		}
		return left.Time < right.Time
	})
	return batch
}

func (a *wakeAggregator) markPublished(batch []receipt, publishedAt time.Time) {
	for _, item := range batch {
		key := wakeKey{TaskID: item.TaskID, DispatchID: item.DispatchID, Event: item.Event}
		a.seen[key] = publishedAt
	}
}

func (a *wakeAggregator) pendingCount() int {
	return len(a.pending)
}

func isWakeEvent(event string) bool {
	return event == "Stop" || event == "TaskCompleted"
}

func publishWake(
	ctx context.Context,
	runID string,
	batch []receipt,
	observedAt time.Time,
	cli string,
	runCommand commandRunner,
) (string, error) {
	if len(batch) == 0 {
		return "", errors.New("cannot publish an empty wake batch")
	}
	if err := validateWakeRunID(runID); err != nil {
		return "", err
	}

	dispatches := make(map[string]struct{})
	var firstEvent, lastEvent time.Time
	for _, item := range batch {
		if !isWakeEvent(item.Event) {
			return "", fmt.Errorf("event %q cannot wake a coordinator", item.Event)
		}
		if err := validateReceipt(item); err != nil {
			return "", fmt.Errorf("invalid wake receipt: %w", err)
		}
		eventTime, _ := time.Parse(time.RFC3339Nano, item.Time)
		if firstEvent.IsZero() || eventTime.Before(firstEvent) {
			firstEvent = eventTime
		}
		if lastEvent.IsZero() || eventTime.After(lastEvent) {
			lastEvent = eventTime
		}
		dispatches[item.TaskID+"\x00"+item.DispatchID] = struct{}{}
	}

	payload := wakeEnvelope{
		Schema:        wakeSchema,
		Version:       1,
		RunID:         runID,
		ReceiptCount:  len(batch),
		DispatchCount: len(dispatches),
		FirstEventAt:  firstEvent.UTC().Format(time.RFC3339Nano),
		LastEventAt:   lastEvent.UTC().Format(time.RFC3339Nano),
		ObservedAt:    observedAt.UTC().Format(time.RFC3339Nano),
		Receipts:      batch,
	}
	payloadJSON, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("encode wake payload: %w", err)
	}
	body := fmt.Sprintf(
		"Observed %d deduplicated Claude completion receipt(s) for %d dispatch(es) in one aggregate. Inspect the payload and exact Dispatch state before acting. This observational signal does not complete an Orca task, Issue, or PR.",
		len(batch),
		len(dispatches),
	)
	output, err := runCommand(
		ctx,
		cli,
		"orchestration", "send",
		"--to", "run:"+runID,
		"--type", "status",
		"--subject", "Claude completion wake",
		"--body", body,
		"--payload", string(payloadJSON),
		"--json",
	)
	if err != nil {
		return "", fmt.Errorf("orca orchestration send: %w: %s", err, strings.TrimSpace(string(output)))
	}

	var response struct {
		OK     bool `json:"ok"`
		Result struct {
			Message struct {
				ID    string `json:"id"`
				RunID string `json:"run_id"`
				Type  string `json:"type"`
			} `json:"message"`
		} `json:"result"`
		Error any `json:"error"`
	}
	if err := json.Unmarshal(output, &response); err != nil {
		return "", fmt.Errorf("decode Orca receipt: %w: %s", err, strings.TrimSpace(string(output)))
	}
	if !response.OK {
		return "", fmt.Errorf("Orca rejected wake signal: %v", response.Error)
	}
	if response.Result.Message.ID == "" || response.Result.Message.RunID != runID || response.Result.Message.Type != "status" {
		return "", fmt.Errorf(
			"Orca wake receipt mismatch: id=%q run=%q type=%q",
			response.Result.Message.ID,
			response.Result.Message.RunID,
			response.Result.Message.Type,
		)
	}
	return response.Result.Message.ID, nil
}

func execCommand(ctx context.Context, name string, args ...string) ([]byte, error) {
	return exec.CommandContext(ctx, name, args...).CombinedOutput()
}

func resolveOrcaCLI(getenv func(string) string) string {
	if configured := strings.TrimSpace(getenv("ORCA_CLI_COMMAND")); configured != "" {
		return configured
	}
	if strings.TrimSpace(getenv("ORCA_DEV_REPO_ROOT")) != "" {
		return "orca-dev"
	}
	return "orca"
}

type synchronizedSink struct {
	mu      sync.Mutex
	encoder *json.Encoder
}

func newReceiptHandler(token string, output io.Writer) http.Handler {
	sink := &synchronizedSink{encoder: json.NewEncoder(output)}
	return newReceiptSinkHandler(token, sink.write)
}

func newReceiptSinkHandler(token string, sink func(receipt) error) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != receiptPath {
			http.NotFound(w, r)
			return
		}
		if r.Method != http.MethodPost {
			w.Header().Set("Allow", http.MethodPost)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		if !sameSecret(r.Header.Get(tokenHeader), token) {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		mediaType, _, err := mime.ParseMediaType(r.Header.Get("Content-Type"))
		if err != nil || mediaType != "application/json" {
			http.Error(w, "content type must be application/json", http.StatusUnsupportedMediaType)
			return
		}

		r.Body = http.MaxBytesReader(w, r.Body, maxReceiptBodyBytes)
		defer r.Body.Close()
		var item receipt
		decoder := json.NewDecoder(r.Body)
		decoder.DisallowUnknownFields()
		if err := decoder.Decode(&item); err != nil {
			http.Error(w, "invalid receipt", http.StatusBadRequest)
			return
		}
		if err := ensureJSONEOF(decoder); err != nil {
			http.Error(w, "invalid receipt", http.StatusBadRequest)
			return
		}
		if err := validateReceipt(item); err != nil {
			http.Error(w, "invalid receipt", http.StatusBadRequest)
			return
		}

		if err := sink(item); err != nil {
			http.Error(w, "receipt sink unavailable", http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
}

func (s *synchronizedSink) write(item receipt) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.encoder.Encode(item)
}

func validateReceipt(r receipt) error {
	if err := validateID("taskId", r.TaskID); err != nil {
		return err
	}
	if err := validateID("dispatchId", r.DispatchID); err != nil {
		return err
	}
	if _, ok := allowedEvents[r.Event]; !ok {
		return errors.New("event is not allowlisted")
	}
	parsed, err := time.Parse(time.RFC3339Nano, r.Time)
	if err != nil || parsed.Location() != time.UTC {
		return errors.New("time must be an RFC3339 UTC timestamp")
	}
	return nil
}

func validateID(name, value string) error {
	if !idPattern.MatchString(value) {
		return fmt.Errorf("%s is missing or invalid", name)
	}
	return nil
}

func readToken(getenv func(string) string) (string, error) {
	token := getenv(tokenEnv)
	if len(token) < 32 || len(token) > 512 || strings.ContainsAny(token, "\r\n") {
		return "", fmt.Errorf("%s must contain 32-512 non-newline bytes", tokenEnv)
	}
	return token, nil
}

func readWakeRunID(getenv func(string) string) (string, error) {
	runID := getenv(wakeRunIDEnv)
	if err := validateWakeRunID(runID); err != nil {
		return "", err
	}
	return runID, nil
}

func validateWakeRunID(runID string) error {
	if !strings.HasPrefix(runID, "run_") || !idPattern.MatchString(runID) {
		return fmt.Errorf("%s is missing or invalid", wakeRunIDEnv)
	}
	return nil
}

func sameSecret(got, expected string) bool {
	if len(got) != len(expected) {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(got), []byte(expected)) == 1
}

func decodeOneJSON(raw []byte, target any, disallowUnknown bool) error {
	decoder := json.NewDecoder(bytes.NewReader(raw))
	if disallowUnknown {
		decoder.DisallowUnknownFields()
	}
	if err := decoder.Decode(target); err != nil {
		return err
	}
	return ensureJSONEOF(decoder)
}

func ensureJSONEOF(decoder *json.Decoder) error {
	var trailing any
	if err := decoder.Decode(&trailing); !errors.Is(err, io.EOF) {
		if err == nil {
			return errors.New("multiple JSON values")
		}
		return err
	}
	return nil
}
