/**
 * HelpCenter — 帮助中心
 * 左侧分类导航 + 右侧内容区，支持 FAQ 手风琴展开/折叠
 */
import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Rocket, Key, FlaskConical, HelpCircle, Keyboard, Info,
  ChevronRight, ChevronDown, X,
  FileUp, Sparkles, PenTool,
  Globe, Server, Cloud,
  Atom, Box, Waves, Palette, Download,
  FileText, Zap, Database, BookOpen, Users, Layers,
  Mail, Heart,
} from 'lucide-react';

/* ── Types ── */
interface NavSection {
  id: string;
  labelKey: string;
  icon: typeof Rocket;
  color: string;
  items: NavItem[];
}

interface NavItem {
  id: string;
  labelKey: string;
  icon: typeof Rocket;
}

/* ── Navigation config ── */
const NAV_SECTIONS: NavSection[] = [
  {
    id: 'getting-started',
    labelKey: 'helpCenter.gettingStarted',
    icon: Rocket,
    color: '#059669',
    items: [
      { id: 'import-papers', labelKey: 'helpCenter.importPapers', icon: FileUp },
      { id: 'ai-assistant', labelKey: 'helpCenter.aiAssistant', icon: Sparkles },
      { id: 'start-writing', labelKey: 'helpCenter.startWriting', icon: PenTool },
    ],
  },
  {
    id: 'api-config',
    labelKey: 'helpCenter.apiConfig',
    icon: Key,
    color: '#7c3aed',
    items: [
      { id: 'api-openai', labelKey: 'helpCenter.apiOpenai', icon: Globe },
      { id: 'api-deepseek', labelKey: 'helpCenter.apiDeepseek', icon: Globe },
      { id: 'api-glm', labelKey: 'helpCenter.apiGlm', icon: Globe },
      { id: 'api-ollama', labelKey: 'helpCenter.apiOllama', icon: Server },
      { id: 'api-siliconflow', labelKey: 'helpCenter.apiSiliconflow', icon: Cloud },
      { id: 'api-claude', labelKey: 'helpCenter.apiClaude', icon: Globe },
      { id: 'api-minimax', labelKey: 'helpCenter.apiMinimax', icon: Globe },
      { id: 'api-errors', labelKey: 'helpCenter.apiErrors', icon: HelpCircle },
    ],
  },
  {
    id: 'plotting',
    labelKey: 'helpCenter.plotting',
    icon: FlaskConical,
    color: '#dc2626',
    items: [
      { id: 'xrd-guide', labelKey: 'helpCenter.xrdGuide', icon: Atom },
      { id: 'rsm3d-guide', labelKey: 'helpCenter.rsm3dGuide', icon: Box },
      { id: 'spectrum-guide', labelKey: 'helpCenter.spectrumGuide', icon: Waves },
      { id: 'journal-theme', labelKey: 'helpCenter.journalTheme', icon: Palette },
      { id: 'export-hd', labelKey: 'helpCenter.exportHd', icon: Download },
    ],
  },
  {
    id: 'faq',
    labelKey: 'helpCenter.faq',
    icon: HelpCircle,
    color: '#d97706',
    items: [
      { id: 'faq-pdf-parse', labelKey: 'helpCenter.faqPdfParse', icon: FileText },
      { id: 'faq-ai-slow', labelKey: 'helpCenter.faqAiSlow', icon: Zap },
      { id: 'faq-data-export', labelKey: 'helpCenter.faqDataExport', icon: Database },
      { id: 'faq-zotero', labelKey: 'helpCenter.faqZotero', icon: BookOpen },
      { id: 'faq-whiteboard', labelKey: 'helpCenter.faqWhiteboard', icon: Layers },
      { id: 'faq-batch-import', labelKey: 'helpCenter.faqBatchImport', icon: Users },
    ],
  },
  {
    id: 'shortcuts',
    labelKey: 'helpCenter.shortcuts',
    icon: Keyboard,
    color: '#0ea5e9',
    items: [],
  },
  {
    id: 'about',
    labelKey: 'helpCenter.about',
    icon: Info,
    color: '#6366f1',
    items: [],
  },
];

/* ── FAQ Accordion Item ── */
const AccordionItem: React.FC<{
  questionKey: string;
  answerKey: string;
  isOpen: boolean;
  onToggle: () => void;
}> = ({ questionKey, answerKey, isOpen, onToggle }) => {
  const { t } = useTranslation();
  return (
    <div style={{
      borderBottom: '1px solid var(--hairline)',
    }}>
      <button
        onClick={onToggle}
        style={{
          display: 'flex', alignItems: 'center', width: '100%',
          padding: '12px 16px', gap: 8,
          background: isOpen ? 'var(--bg-tertiary, rgba(0,0,0,0.04))' : 'transparent',
          border: 'none', cursor: 'pointer', color: 'var(--body)',
          fontSize: 13, fontWeight: 600, textAlign: 'left',
          transition: 'background 0.15s',
        }}
      >
        {isOpen ? <ChevronDown size={16} style={{ flexShrink: 0, color: 'var(--accent)' }} /> : <ChevronRight size={16} style={{ flexShrink: 0, color: 'var(--mute)' }} />}
        <span style={{ flex: 1 }}>{t(questionKey)}</span>
      </button>
      {isOpen && (
        <div style={{
          padding: '4px 16px 16px 40px',
          fontSize: 12.5, lineHeight: 1.7, color: 'var(--body)',
          opacity: 0.85,
        }}>
          {t(answerKey)}
        </div>
      )}
    </div>
  );
};

/* ── Step-by-step instruction block ── */
const StepList: React.FC<{
  steps: string[];
}> = ({ steps }) => {
  const { t } = useTranslation();
  return (
    <ol style={{ margin: '8px 0 0 0', paddingLeft: 0, listStyle: 'none' }}>
      {steps.map((stepKey, idx) => (
        <li key={stepKey} style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          padding: '6px 0', fontSize: 12.5, lineHeight: 1.6, color: 'var(--body)',
        }}>
          <span style={{
            flexShrink: 0, width: 22, height: 22,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            borderRadius: '50%', fontSize: 11, fontWeight: 700,
            background: 'var(--accent)', color: '#fff',
          }}>
            {idx + 1}
          </span>
          <span style={{ paddingTop: 2 }}>{t(stepKey)}</span>
        </li>
      ))}
    </ol>
  );
};

/* ── Keyboard shortcut row ── */
const ShortcutRow: React.FC<{
  actionKey: string;
  keys: string[];
}> = ({ actionKey, keys }) => {
  const { t } = useTranslation();
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '8px 0', borderBottom: '1px solid var(--hairline)',
    }}>
      <span style={{ fontSize: 12.5, color: 'var(--body)' }}>{t(actionKey)}</span>
      <div style={{ display: 'flex', gap: 4 }}>
        {keys.map(k => (
          <kbd key={k} style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            minWidth: 28, height: 24, padding: '0 6px',
            borderRadius: 4, fontSize: 11, fontWeight: 600,
            background: 'var(--bg-tertiary, rgba(0,0,0,0.06))',
            border: '1px solid var(--hairline)',
            color: 'var(--body)', fontFamily: 'inherit',
          }}>
            {k}
          </kbd>
        ))}
      </div>
    </div>
  );
};

/* ── Main Component ── */
interface HelpCenterProps {
  onClose: () => void;
}

export const HelpCenter: React.FC<HelpCenterProps> = ({ onClose }) => {
  const { t } = useTranslation();
  const [activeSection, setActiveSection] = useState('getting-started');
  const [activeItem, setActiveItem] = useState('import-papers');
  const [expandedCategory, setExpandedCategory] = useState('getting-started');
  const [openFaqItems, setOpenFaqItems] = useState<Set<string>>(new Set());

  const toggleFaq = useCallback((id: string) => {
    setOpenFaqItems(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleNavClick = (sectionId: string, itemId: string) => {
    setExpandedCategory(sectionId);
    setActiveSection(sectionId);
    setActiveItem(itemId);
  };

  const handleSectionClick = (sectionId: string) => {
    setExpandedCategory(sectionId);
    setActiveSection(sectionId);
    const section = NAV_SECTIONS.find(s => s.id === sectionId);
    if (section && section.items.length > 0) {
      setActiveItem(section.items[0].id);
    } else {
      setActiveItem(sectionId);
    }
  };

  /* ── Find active info ── */
  const findActiveInfo = () => {
    for (const sec of NAV_SECTIONS) {
      for (const item of sec.items) {
        if (item.id === activeItem) return { section: sec, item };
      }
    }
    const sec = NAV_SECTIONS.find(s => s.id === activeSection);
    return sec ? { section: sec, item: null } : null;
  };

  const activeInfo = findActiveInfo();

  /* ── Render content ── */
  const renderContent = () => {
    // FAQ section
    if (activeSection === 'faq') {
      const faqItems = NAV_SECTIONS.find(s => s.id === 'faq')!.items;
      return (
        <div style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 12 }}>
            {t('helpCenter.faq')}
          </h3>
          <div style={{
            borderRadius: 8, overflow: 'hidden',
            border: '1px solid var(--hairline)',
            background: 'var(--glass-bg, var(--bg-2))',
          }}>
            {faqItems.map(item => (
              <AccordionItem
                key={item.id}
                questionKey={item.labelKey}
                answerKey={`helpCenter.${item.id}Answer`}
                isOpen={openFaqItems.has(item.id)}
                onToggle={() => toggleFaq(item.id)}
              />
            ))}
          </div>
        </div>
      );
    }

    // Shortcuts section
    if (activeSection === 'shortcuts') {
      return (
        <div style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 12 }}>
            {t('helpCenter.shortcuts')}
          </h3>
          <div style={{
            borderRadius: 8, padding: '8px 16px',
            border: '1px solid var(--hairline)',
            background: 'var(--glass-bg, var(--bg-2))',
          }}>
            <ShortcutRow actionKey="helpCenter.scSearch" keys={['Ctrl', 'K']} />
            <ShortcutRow actionKey="helpCenter.scNewNote" keys={['Ctrl', 'N']} />
            <ShortcutRow actionKey="helpCenter.scGraph" keys={['Ctrl', 'Shift', 'G']} />
            <ShortcutRow actionKey="helpCenter.scWriting" keys={['Ctrl', 'Shift', 'W']} />
            <ShortcutRow actionKey="helpCenter.scEscape" keys={['Esc']} />
            <ShortcutRow actionKey="helpCenter.scSend" keys={['Enter']} />
            <ShortcutRow actionKey="helpCenter.scNewline" keys={['Shift', 'Enter']} />
          </div>
        </div>
      );
    }

    // About section
    if (activeSection === 'about') {
      return (
        <div style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 16 }}>
            {t('helpCenter.about')}
          </h3>
          <div style={{
            borderRadius: 8, padding: 20,
            border: '1px solid var(--hairline)',
            background: 'var(--glass-bg, var(--bg-2))',
            textAlign: 'center',
          }}>
            <div style={{
              width: 56, height: 56, borderRadius: 14,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 12px', fontSize: 24, fontWeight: 800, color: '#fff',
            }}>
              A
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--body)', marginBottom: 4 }}>
              AcaSight
            </div>
            <div style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 16 }}>
              {t('helpCenter.aboutVersion')}
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--body)', lineHeight: 1.7, opacity: 0.8, marginBottom: 16 }}>
              {t('helpCenter.aboutDesc')}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 12, color: 'var(--mute)' }}>
              <Mail size={14} />
              <span>acasight@example.com</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 12, color: 'var(--mute)', marginTop: 6 }}>
              <Heart size={14} style={{ color: '#ef4444' }} />
              <span>{t('helpCenter.aboutMadeWithLove')}</span>
            </div>
          </div>
        </div>
      );
    }

    // Getting Started section
    if (activeSection === 'getting-started') {
      if (activeItem === 'import-papers') {
        return (
          <div style={{ padding: '16px 20px' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 8 }}>
              {t('helpCenter.importPapers')}
            </h3>
            <p style={{ fontSize: 12.5, color: 'var(--body)', opacity: 0.75, lineHeight: 1.6, marginBottom: 12 }}>
              {t('helpCenter.importPapersDesc')}
            </p>
            <StepList steps={[
              'helpCenter.importStep1',
              'helpCenter.importStep2',
              'helpCenter.importStep3',
              'helpCenter.importStep4',
            ]} />
          </div>
        );
      }
      if (activeItem === 'ai-assistant') {
        return (
          <div style={{ padding: '16px 20px' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 8 }}>
              {t('helpCenter.aiAssistant')}
            </h3>
            <p style={{ fontSize: 12.5, color: 'var(--body)', opacity: 0.75, lineHeight: 1.6, marginBottom: 12 }}>
              {t('helpCenter.aiAssistantDesc')}
            </p>
            <StepList steps={[
              'helpCenter.aiStep1',
              'helpCenter.aiStep2',
              'helpCenter.aiStep3',
            ]} />
          </div>
        );
      }
      if (activeItem === 'start-writing') {
        return (
          <div style={{ padding: '16px 20px' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 8 }}>
              {t('helpCenter.startWriting')}
            </h3>
            <p style={{ fontSize: 12.5, color: 'var(--body)', opacity: 0.75, lineHeight: 1.6, marginBottom: 12 }}>
              {t('helpCenter.startWritingDesc')}
            </p>
            <StepList steps={[
              'helpCenter.writingStep1',
              'helpCenter.writingStep2',
              'helpCenter.writingStep3',
              'helpCenter.writingStep4',
            ]} />
          </div>
        );
      }
    }

    // API Configuration section
    if (activeSection === 'api-config') {
      const apiStepsMap: Record<string, string[]> = {
        'api-openai': ['helpCenter.apiOpenaiStep1', 'helpCenter.apiOpenaiStep2', 'helpCenter.apiOpenaiStep3', 'helpCenter.apiOpenaiStep4'],
        'api-deepseek': ['helpCenter.apiDeepseekStep1', 'helpCenter.apiDeepseekStep2', 'helpCenter.apiDeepseekStep3', 'helpCenter.apiDeepseekStep4'],
        'api-glm': ['helpCenter.apiGlmStep1', 'helpCenter.apiGlmStep2', 'helpCenter.apiGlmStep3', 'helpCenter.apiGlmStep4'],
        'api-ollama': ['helpCenter.apiOllamaStep1', 'helpCenter.apiOllamaStep2', 'helpCenter.apiOllamaStep3', 'helpCenter.apiOllamaStep4'],
        'api-siliconflow': ['helpCenter.apiSiliconflowStep1', 'helpCenter.apiSiliconflowStep2', 'helpCenter.apiSiliconflowStep3', 'helpCenter.apiSiliconflowStep4'],
        'api-claude': ['helpCenter.apiClaudeStep1', 'helpCenter.apiClaudeStep2', 'helpCenter.apiClaudeStep3', 'helpCenter.apiClaudeStep4'],
        'api-minimax': ['helpCenter.apiMinimaxStep1', 'helpCenter.apiMinimaxStep2', 'helpCenter.apiMinimaxStep3', 'helpCenter.apiMinimaxStep4'],
        'api-errors': [],
      };

      const descMap: Record<string, string> = {
        'api-openai': 'helpCenter.apiOpenaiDesc',
        'api-deepseek': 'helpCenter.apiDeepseekDesc',
        'api-glm': 'helpCenter.apiGlmDesc',
        'api-ollama': 'helpCenter.apiOllamaDesc',
        'api-siliconflow': 'helpCenter.apiSiliconflowDesc',
        'api-claude': 'helpCenter.apiClaudeDesc',
        'api-minimax': 'helpCenter.apiMinimaxDesc',
        'api-errors': '',
      };

      if (activeItem === 'api-errors') {
        const errorFaqs = [
          'helpCenter.error401', 'helpCenter.error429', 'helpCenter.error500', 'helpCenter.errorTimeout',
        ];
        return (
          <div style={{ padding: '16px 20px' }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 12 }}>
              {t('helpCenter.apiErrors')}
            </h3>
            <div style={{
              borderRadius: 8, overflow: 'hidden',
              border: '1px solid var(--hairline)',
              background: 'var(--glass-bg, var(--bg-2))',
            }}>
              {errorFaqs.map(key => (
                <AccordionItem
                  key={key}
                  questionKey={key}
                  answerKey={`${key}Answer`}
                  isOpen={openFaqItems.has(key)}
                  onToggle={() => toggleFaq(key)}
                />
              ))}
            </div>
          </div>
        );
      }

      const steps = apiStepsMap[activeItem] || [];
      const desc = descMap[activeItem] || '';
      const itemInfo = NAV_SECTIONS.find(s => s.id === 'api-config')?.items.find(i => i.id === activeItem);

      return (
        <div style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 8 }}>
            {itemInfo ? t(itemInfo.labelKey) : ''}
          </h3>
          {desc && (
            <p style={{ fontSize: 12.5, color: 'var(--body)', opacity: 0.75, lineHeight: 1.6, marginBottom: 12 }}>
              {t(desc)}
            </p>
          )}
          {steps.length > 0 && <StepList steps={steps} />}
        </div>
      );
    }

    // Plotting section
    if (activeSection === 'plotting') {
      const plotDescMap: Record<string, string> = {
        'xrd-guide': 'helpCenter.xrdGuideDesc',
        'rsm3d-guide': 'helpCenter.rsm3dGuideDesc',
        'spectrum-guide': 'helpCenter.spectrumGuideDesc',
        'journal-theme': 'helpCenter.journalThemeDesc',
        'export-hd': 'helpCenter.exportHdDesc',
      };
      const plotStepsMap: Record<string, string[]> = {
        'xrd-guide': ['helpCenter.xrdStep1', 'helpCenter.xrdStep2', 'helpCenter.xrdStep3', 'helpCenter.xrdStep4'],
        'rsm3d-guide': ['helpCenter.rsm3dStep1', 'helpCenter.rsm3dStep2', 'helpCenter.rsm3dStep3'],
        'spectrum-guide': ['helpCenter.spectrumStep1', 'helpCenter.spectrumStep2', 'helpCenter.spectrumStep3'],
        'journal-theme': ['helpCenter.themeStep1', 'helpCenter.themeStep2', 'helpCenter.themeStep3'],
        'export-hd': ['helpCenter.exportStep1', 'helpCenter.exportStep2', 'helpCenter.exportStep3'],
      };

      const itemInfo = NAV_SECTIONS.find(s => s.id === 'plotting')?.items.find(i => i.id === activeItem);
      const desc = plotDescMap[activeItem] || '';
      const steps = plotStepsMap[activeItem] || [];

      return (
        <div style={{ padding: '16px 20px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--body)', marginBottom: 8 }}>
            {itemInfo ? t(itemInfo.labelKey) : ''}
          </h3>
          {desc && (
            <p style={{ fontSize: 12.5, color: 'var(--body)', opacity: 0.75, lineHeight: 1.6, marginBottom: 12 }}>
              {t(desc)}
            </p>
          )}
          {steps.length > 0 && <StepList steps={steps} />}
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--canvas)' }}>
      {/* ── Left sidebar navigation ── */}
      <div style={{
        width: 220, flexShrink: 0,
        borderRight: '1px solid var(--hairline)',
        background: 'var(--bg-2, var(--bg-secondary))',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Sidebar header */}
        <div style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--hairline)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <HelpCircle size={18} style={{ color: '#6366f1' }} />
            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--body)' }}>
              {t('helpCenter.title')}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--mute)', padding: 4, borderRadius: 4,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav sections */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 0' }}>
          {NAV_SECTIONS.map(sec => {
            const isExpanded = expandedCategory === sec.id;
            const hasActiveChild = sec.items.some(c => c.id === activeItem) || activeSection === sec.id;
            const isLeaf = sec.items.length === 0;
            return (
              <div key={sec.id}>
                {/* Section header */}
                <button
                  onClick={() => {
                    if (isLeaf) {
                      handleSectionClick(sec.id);
                    } else {
                      setExpandedCategory(isExpanded ? '' : sec.id);
                      handleSectionClick(sec.id);
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', width: '100%',
                    padding: '8px 14px', gap: 8,
                    background: hasActiveChild ? 'var(--bg-tertiary, rgba(0,0,0,0.04))' : 'transparent',
                    border: 'none', cursor: 'pointer', color: 'var(--body)',
                    fontSize: 13, fontWeight: 600, textAlign: 'left',
                  }}
                >
                  <sec.icon size={16} style={{ color: sec.color, flexShrink: 0 }} />
                  <span style={{ flex: 1 }}>{t(sec.labelKey)}</span>
                  {!isLeaf && (
                    <ChevronRight
                      size={14}
                      style={{
                        color: 'var(--mute)',
                        transform: isExpanded ? 'rotate(90deg)' : 'rotate(0)',
                        transition: 'transform 0.15s',
                      }}
                    />
                  )}
                </button>

                {/* Children */}
                {isExpanded && sec.items.map(item => {
                  const isActive = activeItem === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(sec.id, item.id)}
                      style={{
                        display: 'flex', alignItems: 'center', width: '100%',
                        padding: '6px 14px 6px 38px', gap: 8,
                        background: isActive
                          ? `linear-gradient(90deg, ${sec.color}18, transparent)`
                          : 'transparent',
                        border: 'none', cursor: 'pointer',
                        borderLeft: isActive ? `3px solid ${sec.color}` : '3px solid transparent',
                        color: isActive ? sec.color : 'var(--body)',
                        fontSize: 12.5, fontWeight: isActive ? 600 : 400,
                        textAlign: 'left',
                      }}
                    >
                      <item.icon size={14} style={{ flexShrink: 0 }} />
                      <span style={{ flex: 1 }}>{t(item.labelKey)}</span>
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Right content area ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top toolbar */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '8px 16px',
          borderBottom: '1px solid var(--hairline)',
          background: 'var(--bg-2, var(--bg-secondary))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {activeInfo && (
              <>
                <activeInfo.section.icon size={16} style={{ color: activeInfo.section.color }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>
                  {activeInfo.item ? t(activeInfo.item.labelKey) : t(activeInfo.section.labelKey)}
                </span>
                {activeInfo.item && (
                  <span style={{
                    fontSize: 11, padding: '2px 8px', borderRadius: 8,
                    background: `${activeInfo.section.color}20`, color: activeInfo.section.color,
                    fontWeight: 500,
                  }}>
                    {t(activeInfo.section.labelKey)}
                  </span>
                )}
              </>
            )}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
};
