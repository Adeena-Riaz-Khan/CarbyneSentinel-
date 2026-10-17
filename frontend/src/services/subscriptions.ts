import type { Transaction } from "../contracts/domain";
import { getTransactions } from "./apiClient";

export type Unsubscribe = () => void;

/**
 * Polling subscription for mempool feed.
 * Always returns an unsubscribe that clears the interval and aborts in-flight work.
 */
export function subscribeTransactions(
  onData: (txs: Transaction[]) => void,
  onError: (err: unknown) => void,
  intervalMs = 500,
): Unsubscribe {
  let stopped = false;
  let controller: AbortController | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;

  const tick = async () => {
    if (stopped) return;
    controller?.abort();
    controller = new AbortController();
    try {
      const txs = await getTransactions(controller.signal);
      if (!stopped) onData(txs);
    } catch (e) {
      if (!stopped) onError(e);
    }
  };

  void tick();
  timer = setInterval(() => void tick(), intervalMs);

  return () => {
    stopped = true;
    if (timer) clearInterval(timer);
    timer = null;
    controller?.abort();
    controller = null;
  };
}
