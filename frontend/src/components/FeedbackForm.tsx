interface FeedbackFormProps {
  title: string;
  text: string;
  setText: (value: string) => void;
  loading: boolean;
  error: string | null;
  onSubmit: () => Promise<void> | void;
}

export default function FeedbackForm({
  title,
  text,
  setText,
  loading,
  error,
  onSubmit,
}: FeedbackFormProps) {
  return (
    <>
      <h3 className="section-title">{title}</h3>
      <div className="flex gap-4 items-center">
        <textarea
          className="flex-1 border-2 border-slate-200 rounded-lg p-4 text-sm resize-none focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-colors placeholder:text-slate-400"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Share your thoughts, suggestions, or report issues..."
          rows={3}
        />

        <button
          type="button"
          onClick={() => void onSubmit()}
          disabled={loading || !text.trim()}
          className="px-6 py-3 h-fit rounded-lg text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors shadow-sm hover:shadow-md"
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
        <div className="mt-3 px-4 py-2 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm font-medium">{error}</p>
        </div>
      )}
    </>
  );
}
