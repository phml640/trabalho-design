import { useCallback, useEffect, useRef, useState } from 'react';

export function usePolling<T>(
  key: string,
  load: (signal: AbortSignal) => Promise<T>,
  enabled = true,
) {
  const [revision, setRevision] = useState(0);
  const [state, setState] = useState<{
    key: string;
    data?: T;
    error?: Error;
    loading: boolean;
    updatedAt?: Date;
  }>({ key, loading: enabled });
  useEffect(() => {
    if (!enabled) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function update() {
      setState((previous) => ({ ...(previous.key === key ? previous : { key }), loading: true }));
      try {
        const data = await load(controller.signal);
        if (active) setState({ key, data, loading: false, updatedAt: new Date() });
      } catch (error) {
        if (active)
          setState((previous) => ({
            ...previous,
            key,
            error: error instanceof Error ? error : new Error('Falha ao atualizar.'),
            loading: false,
          }));
      } finally {
        if (active) timer = setTimeout(update, 3000);
      }
    }
    void update();
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [key, load, enabled, revision]);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  const current =
    state.key === key && enabled
      ? state
      : { loading: enabled, data: undefined, error: undefined, updatedAt: undefined };
  return { ...current, refresh };
}

export function useAction() {
  const locked = useRef(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; text: string }>();
  const run = async (operation: () => Promise<void>, message?: string) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setFeedback(undefined);
    try {
      await operation();
      if (message) setFeedback({ kind: 'success', text: message });
    } catch (error) {
      setFeedback({
        kind: 'error',
        text: error instanceof Error ? error.message : 'Não foi possível concluir a operação.',
      });
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };
  return { busy, feedback, run, setFeedback };
}
