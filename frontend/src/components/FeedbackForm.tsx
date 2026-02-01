import { useState } from "react";

interface FeedbackFormProps {
  title: string;
  loading: boolean;
  error: string | null;
  onSubmit: (text: string) => Promise<boolean> | boolean;
}

export default function FeedbackForm({
  title,
  loading,
  error,
  onSubmit,
}: FeedbackFormProps) {
  const [text, setText] = useState("");

  const handleSubmit = async () => {
    if (!text.trim()) return;
    const result = await onSubmit(text);
    if (result) {
      setText("");
    }
  };

  return (
    <>
      {title && <h3 className="section-title">{title}</h3>}
      <div className="flex gap-3 items-center">
        <textarea
          className="flex-1 p-4 text-sm resize-none transition-colors theme-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Share your thoughts, suggestions, or report issues..."
          rows={3}
        />

        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={loading || !text.trim()}
          className="px-6 py-3 h-fit rounded-md text-sm font-semibold transition-colors shadow-sm hover:shadow-md theme-button"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing...
            </span>
          ) : (
            "Submit"
          )}
        </button>
      </div>

      {error && (
        <div className="mt-3 px-4 py-2 theme-alert">
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}
    </>
  );
}
