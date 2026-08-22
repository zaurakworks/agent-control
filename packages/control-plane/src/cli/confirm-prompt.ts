/**
 * Reads one line of interactive `y`/`n` confirmation from stdin. Used by
 * `configs use`/`configs switch` when `--yes` is not passed. Case
 * insensitive; only `y`/`yes` are treated as an affirmative answer --
 * everything else (including empty input) is a rejection.
 */
export async function readYesNo(promptText: string): Promise<boolean> {
  process.stdout.write(promptText);
  const line = await readLine();
  const normalized = line.trim().toLowerCase();
  return normalized === 'y' || normalized === 'yes';
}

function readLine(): Promise<string> {
  return new Promise((resolve) => {
    const stdin = process.stdin;
    stdin.resume();
    stdin.setEncoding('utf8');
    const onData = (chunk: string) => {
      stdin.pause();
      stdin.removeListener('data', onData);
      resolve(chunk.split('\n')[0] ?? '');
    };
    stdin.once('data', onData);
  });
}
