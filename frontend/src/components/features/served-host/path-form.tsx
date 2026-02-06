import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface PathFormProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export function PathForm({ value, onChange, onSubmit }: PathFormProps) {
  const { t } = useTranslation();

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="flex-1 flex items-center gap-2"
    >
      <input
        name="url"
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-transparent px-3 py-1.5 rounded-md border border-neutral-600 text-sm text-neutral-200 placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="http://localhost:8011/"
      />
      <button
        type="submit"
        className="px-3 py-1.5 text-sm rounded-md bg-blue-500 text-white hover:bg-blue-600 transition-colors"
      >
        {t(I18nKey.SERVED_APP$GO_BUTTON)}
      </button>
    </form>
  );
}
