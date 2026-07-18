import React, { useState, useEffect, useRef } from "react";
import { X, Languages, Loader2, Copy, Check } from "lucide-react";
import { translateApi } from "@/services/api";

interface FullPageTranslateProps {
  text: string;
  onClose: () => void;
}

export const FullPageTranslate: React.FC<FullPageTranslateProps> = ({ text, onClose }) => {
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("zh");
  const [copied, setCopied] = useState(false);
  const [progress, setProgress] = useState("");
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    translateLong();
  }, [sourceLang, targetLang]);

  const translateLong = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setProgress("正在翻译...");
    try {
      const res = await translateApi.long({
        text,
        source_lang: sourceLang,
        target_lang: targetLang,
      });
      setResult(res.data.translation);
      setProgress("");
      if (res.data.error) {
        setError(res.data.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "翻译失败");
    } finally {
      setLoading(false);
      setProgress("");
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const sourceLangName = sourceLang === "auto" ? "自动检测" :
    sourceLang === "en" ? "英文" :
    sourceLang === "zh" ? "中文" : sourceLang;
  const targetLangName = targetLang === "en" ? "英文" :
    targetLang === "zh" ? "中文" :
    targetLang === "ja" ? "日文" : targetLang;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 10001,
        background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 20,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          width: "90%", maxWidth: 900, height: "85vh",
          background: "var(--canvas, #1e1e2e)",
          border: "1px solid var(--hairline, #333)",
          borderRadius: 12,
          display: "flex", flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 12px 48px rgba(0,0,0,0.4)",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "12px 16px",
          borderBottom: "1px solid var(--hairline, #333)",
          background: "var(--accent-bg-soft, rgba(99,102,241,0.06))",
        }}>
          <Languages size={16} style={{ color: "var(--accent, #6366f1)" }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: "var(--body, #ddd)", flex: 1 }}>
            全文翻译
          </span>

          {/* Language selector */}
          <div style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12 }}>
            <select
              value={sourceLang}
              onChange={(e) => setSourceLang(e.target.value)}
              style={selectStyle}
            >
              <option value="auto">自动检测</option>
              <option value="en">英文</option>
              <option value="zh">中文</option>
              <option value="ja">日文</option>
              <option value="ko">韩文</option>
              <option value="fr">法文</option>
              <option value="de">德文</option>
              <option value="es">西班牙文</option>
              <option value="ru">俄文</option>
            </select>
            <span style={{ color: "var(--mute, #888)" }}>→</span>
            <select
              value={targetLang}
              onChange={(e) => setTargetLang(e.target.value)}
              style={selectStyle}
            >
              <option value="zh">中文</option>
              <option value="en">英文</option>
              <option value="ja">日文</option>
              <option value="ko">韩文</option>
              <option value="fr">法文</option>
              <option value="de">德文</option>
            </select>
          </div>

          <button onClick={onClose} style={closeBtnStyle}>
            <X size={16} />
          </button>
        </div>

        {/* Body: side by side */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Source */}
          <div style={{
            flex: 1, display: "flex", flexDirection: "column",
            borderRight: "1px solid var(--hairline, #333)",
          }}>
            <div style={{
              padding: "8px 14px", fontSize: 11, fontWeight: 600,
              color: "var(--mute, #888)", background: "var(--bg-2, #2a2a3e)",
              borderBottom: "1px solid var(--hairline, #333)",
            }}>
              原文 ({sourceLangName}) · {text.length} 字符
            </div>
            <div style={{
              flex: 1, overflow: "auto", padding: 14,
              fontSize: 13, lineHeight: 1.7, color: "var(--body, #ccc)",
              whiteSpace: "pre-wrap", wordBreak: "break-word",
            }}>
              {text}
            </div>
          </div>

          {/* Translation */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div style={{
              padding: "8px 14px", fontSize: 11, fontWeight: 600,
              color: "var(--mute, #888)", background: "var(--bg-2, #2a2a3e)",
              borderBottom: "1px solid var(--hairline, #333)",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <span>译文 ({targetLangName})</span>
              <div style={{ display: "flex", gap: 4 }}>
                {result && (
                  <button onClick={handleCopy} style={iconBtnStyle}>
                    {copied ? <Check size={11} /> : <Copy size={11} />}
                    {copied ? "已复制" : ""}
                  </button>
                )}
                {loading && <Loader2 size={14} className="animate-spin" />}
              </div>
            </div>
            <div
              ref={resultRef}
              style={{
                flex: 1, overflow: "auto", padding: 14,
                fontSize: 13, lineHeight: 1.7, color: "var(--body, #ddd)",
                whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}
            >
              {loading ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--mute, #888)", justifyContent: "center", paddingTop: 40 }}>
                  <Loader2 size={20} className="animate-spin" />
                  {progress || "翻译中..."}
                </div>
              ) : error ? (
                <div style={{ color: "var(--danger, #ef4444)", padding: 12, background: "rgba(239,68,68,0.08)", borderRadius: 8 }}>
                  {error}
                  <button
                    onClick={translateLong}
                    style={{
                      display: "block", marginTop: 8, padding: "6px 14px",
                      borderRadius: 6, border: "1px solid var(--hairline, #444)",
                      background: "transparent", color: "var(--body, #ccc)", cursor: "pointer", fontSize: 12,
                    }}
                  >
                    重试
                  </button>
                </div>
              ) : result ? (
                result
              ) : (
                <div style={{ color: "var(--mute, #666)", fontStyle: "italic" }}>
                  等待翻译...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const selectStyle: React.CSSProperties = {
  padding: "4px 8px", borderRadius: 6, border: "1px solid var(--hairline, #444)",
  background: "var(--canvas, #1e1e2e)", color: "var(--body, #ccc)",
  fontSize: 12, cursor: "pointer", outline: "none",
};

const closeBtnStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center",
  width: 28, height: 28, borderRadius: 6, border: "none",
  background: "transparent", color: "var(--mute, #888)",
  cursor: "pointer",
};

const iconBtnStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", gap: 4,
  padding: "3px 8px", borderRadius: 4, border: "none",
  background: "transparent", color: "var(--mute, #888)",
  cursor: "pointer", fontSize: 10,
};

export default FullPageTranslate;
