import React from "react";
import { FaArrowRotateRight } from "react-icons/fa6";
import { FaExternalLinkAlt, FaHome } from "react-icons/fa";
import { useTranslation } from "react-i18next";
import { useUnifiedActiveHost } from "#/hooks/query/use-unified-active-host";
import { PathForm } from "#/components/features/served-host/path-form";
import { I18nKey } from "#/i18n/declaration";
import ServerProcessIcon from "#/icons/server-process.svg?react";
import { useConversationStore } from "#/stores/conversation-store";

function ServedApp() {
  const { t } = useTranslation();
  const { activeHost } = useUnifiedActiveHost();
  const { servedPreview } = useConversationStore();
  const [refreshKey, setRefreshKey] = React.useState(0);
  const [currentActiveHost, setCurrentActiveHost] = React.useState<
    string | null
  >(null);
  const [path, setPath] = React.useState<string>("");
  const [urlInput, setUrlInput] = React.useState<string>("");
  const previewOverrideRef = React.useRef(false);

  const applyUrl = (url: URL, shouldOverride: boolean) => {
    previewOverrideRef.current = shouldOverride;
    setCurrentActiveHost(url.origin);
    setPath(url.pathname + url.search);
    setUrlInput(url.toString());
    setRefreshKey((prev) => prev + 1);
  };

  const resetUrl = React.useCallback(() => {
    previewOverrideRef.current = false;
    if (activeHost) {
      applyUrl(new URL("/", activeHost), false);
    } else {
      setCurrentActiveHost(null);
      setPath("");
      setUrlInput("");
    }
  }, [activeHost]);

  const buildUrlFromInput = (
    input: string,
    fallbackOrigin: string | null,
  ): URL | null => {
    const trimmed = input.trim();
    if (!trimmed) {
      return null;
    }

    try {
      return new URL(trimmed);
    } catch {
      // Continue to normalized parsing.
    }

    const looksLikeHost =
      trimmed.startsWith("localhost") ||
      trimmed.includes(".") ||
      trimmed.includes(":");

    if (looksLikeHost) {
      try {
        return new URL(`http://${trimmed}`);
      } catch {
        return null;
      }
    }

    if (fallbackOrigin) {
      const pathValue = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
      try {
        return new URL(pathValue, fallbackOrigin);
      } catch {
        return null;
      }
    }

    return null;
  };

  React.useEffect(() => {
    if (!previewOverrideRef.current) {
      resetUrl();
    }
  }, [activeHost, resetUrl]);

  React.useEffect(() => {
    if (!servedPreview || servedPreview.requestId === 0) {
      return;
    }

    try {
      const url = new URL(servedPreview.url);
      applyUrl(url, true);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error("Failed to parse preview URL:", e);
    }
  }, [servedPreview]);

  const fullUrl = currentActiveHost
    ? new URL(path || "/", currentActiveHost).toString()
    : "";
  const hasActiveHost = Boolean(currentActiveHost);

  return (
    <div className="h-full w-full flex flex-col">
      <div className="w-full p-2 flex items-center gap-4 border-b border-neutral-600">
        <button
          type="button"
          onClick={() => {
            if (!fullUrl) {
              return;
            }
            window.open(fullUrl, "_blank");
          }}
          className="text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label={t(I18nKey.BUTTON$OPEN_IN_NEW_TAB)}
          disabled={!hasActiveHost}
        >
          <FaExternalLinkAlt className="w-4 h-4" />
        </button>
        <button
          type="button"
          onClick={() => setRefreshKey((prev) => prev + 1)}
          className="text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label={t(I18nKey.BUTTON$REFRESH)}
          disabled={!hasActiveHost}
        >
          <FaArrowRotateRight className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => resetUrl()}
          className="text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label={t(I18nKey.BUTTON$HOME)}
          disabled={!hasActiveHost}
        >
          <FaHome className="w-4 h-4" />
        </button>
        <div className="w-full flex">
          <PathForm
            value={urlInput}
            onChange={setUrlInput}
            onSubmit={() => {
              const nextUrl = buildUrlFromInput(urlInput, currentActiveHost);
              if (nextUrl) {
                applyUrl(nextUrl, true);
              }
            }}
          />
        </div>
      </div>
      {hasActiveHost ? (
        <iframe
          key={refreshKey}
          title={t(I18nKey.SERVED_APP$TITLE)}
          src={fullUrl}
          className="w-full flex-1 custom-scrollbar-always"
        />
      ) : (
        <div className="flex flex-col items-center justify-center w-full flex-1 p-10">
          <ServerProcessIcon width={113} height={113} color="#A1A1A1" />
          <span className="text-[#8D95A9] text-[19px] font-normal leading-5">
            {t(I18nKey.BROWSER$SERVER_MESSAGE)}
          </span>
        </div>
      )}
    </div>
  );
}

export default ServedApp;
