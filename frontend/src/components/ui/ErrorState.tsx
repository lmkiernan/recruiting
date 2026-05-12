interface Props {
  message?: string;
}

export function ErrorState({ message = "Something went wrong." }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-red-400">
      <svg className="w-10 h-10 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <p className="text-sm">{message}</p>
    </div>
  );
}
