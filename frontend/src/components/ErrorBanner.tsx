type Props = {
  message: string;
  onDismiss?: () => void;
};

export function ErrorBanner({ message, onDismiss }: Props) {
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onDismiss ? (
        <button type="button" onClick={onDismiss} aria-label="Dismiss error">
          Dismiss
        </button>
      ) : null}
    </div>
  );
}
