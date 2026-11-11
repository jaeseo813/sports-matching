import { useId, type InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

// 라벨 + 입력 + 필드 옆 에러 텍스트 (색만으로 상태를 구분하지 않는다)
export default function Field({ label, error, ...input }: Props) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-sm font-bold">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        className="min-h-11 w-full rounded-lg border border-edge bg-white px-3 text-sm"
        {...input}
      />
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm font-semibold text-night">
          ⚠ {error}
        </p>
      )}
    </div>
  );
}
