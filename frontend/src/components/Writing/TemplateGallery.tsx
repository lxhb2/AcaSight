import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, Plus, Search, Tag, ChevronDown, Loader2, AlertTriangle, Check, X, Trash2 } from 'lucide-react';
import { writingTemplatesApi, type WritingTemplate } from '@/services/api';

interface TemplateGalleryProps {
  onApply?: (template: WritingTemplate) => void;
}

export const TemplateGallery: React.FC<TemplateGalleryProps> = ({ onApply }) => {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState<WritingTemplate[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createCategory, setCreateCategory] = useState('');
  const [creating, setCreating] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await writingTemplatesApi.list();
      setTemplates(res.data ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const res = await writingTemplatesApi.getCategories();
      setCategories(res.data ?? []);
    } catch (_e: unknown) {
      // silent
    }
  }, []);

  useEffect(() => {
    loadTemplates();
    loadCategories();
  }, [loadTemplates, loadCategories]);

  const handleCreate = useCallback(async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      await writingTemplatesApi.create({
        name: createName,
        description: createDesc,
        category: createCategory || 'custom',
        tags: [],
        sections: [],
        style: {},
        is_builtin: false,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDesc('');
      setCreateCategory('');
      await loadTemplates();
      await loadCategories();
    } catch (_e: unknown) {
      // silent
    } finally {
      setCreating(false);
    }
  }, [createName, createDesc, createCategory, loadTemplates, loadCategories]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await writingTemplatesApi.delete(id);
      await loadTemplates();
    } catch (_e: unknown) {
      // silent
    }
  }, [loadTemplates]);

  const filtered = useMemo(() => templates.filter((t) => {
    if (selectedCategory && t.category !== selectedCategory) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q);
    }
    return true;
  }), [templates, selectedCategory, searchQuery]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'var(--ink)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--hairline)' }}>
        <BookOpen size={16} style={{ color: 'var(--accent)' }} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>{t('templateGallery.title')}</span>
        <button
          onClick={() => setShowCreate(!showCreate)}
          style={{ marginLeft: 'auto', padding: '4px 8px', borderRadius: 6, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}
        >
          <Plus size={12} /> {t('templateGallery.create')}
        </button>
      </div>

      {showCreate && (
        <div style={{ padding: 12, borderBottom: '1px solid var(--hairline)', background: 'var(--canvas)', animation: 'floating-panel-appear 0.15s ease' }}>
          <input
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder={t('templateGallery.templateName')}
            style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--surface)', color: 'var(--ink)', fontSize: 13, marginBottom: 8, outline: 'none' }}
          />
          <textarea
            value={createDesc}
            onChange={(e) => setCreateDesc(e.target.value)}
            placeholder={t('templateGallery.templateDesc')}
            rows={2}
            style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--surface)', color: 'var(--ink)', fontSize: 13, marginBottom: 8, outline: 'none', resize: 'vertical' }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={createCategory}
              onChange={(e) => setCreateCategory(e.target.value)}
              placeholder={t('templateGallery.category')}
              style={{ flex: 1, padding: '6px 10px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--surface)', color: 'var(--ink)', fontSize: 13, outline: 'none' }}
            />
            <button onClick={handleCreate} disabled={creating || !createName.trim()} style={{ padding: '6px 16px', borderRadius: 6, background: 'var(--accent)', color: '#fff', border: 'none', cursor: creating ? 'wait' : 'pointer', fontSize: 12 }}>
              {creating ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
            </button>
            <button onClick={() => setShowCreate(false)} style={{ padding: '6px 10px', borderRadius: 6, background: 'transparent', border: '1px solid var(--hairline)', cursor: 'pointer', color: 'var(--mute)' }}>
              <X size={12} />
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, padding: '8px 16px', borderBottom: '1px solid var(--hairline)', alignItems: 'center' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--mute)' }} />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('templateGallery.searchPlaceholder')}
            style={{ width: '100%', padding: '4px 8px 4px 26px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--surface)', color: 'var(--ink)', fontSize: 12, outline: 'none' }}
          />
        </div>
      </div>

      {categories.length > 0 && (
        <div style={{ display: 'flex', gap: 4, padding: '6px 16px', borderBottom: '1px solid var(--hairline)', flexWrap: 'wrap' }}>
          <button
            onClick={() => setSelectedCategory(null)}
            style={{ padding: '2px 8px', borderRadius: 4, border: 'none', background: !selectedCategory ? 'var(--accent)' : 'var(--surface)', color: !selectedCategory ? '#fff' : 'var(--ink)', cursor: 'pointer', fontSize: 11 }}
          >
            {t('templateGallery.all')}
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
              style={{ padding: '2px 8px', borderRadius: 4, border: 'none', background: cat === selectedCategory ? 'var(--accent)' : 'var(--surface)', color: cat === selectedCategory ? '#fff' : 'var(--ink)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}
            >
              <Tag size={9} />{cat}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertTriangle size={12} />{error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
          <Loader2 size={16} className="animate-spin" />
          <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('templateGallery.loading')}</span>
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
          <BookOpen size={24} style={{ color: 'var(--mute)' }} />
          <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('templateGallery.noTemplates')}</span>
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {filtered.map((tmpl) => (
            <div key={tmpl.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
              <div
                style={{ display: 'flex', alignItems: 'center', padding: '8px 16px', cursor: 'pointer', gap: 8 }}
                onClick={() => setExpandedId(expandedId === tmpl.id ? null : tmpl.id)}
              >
                <BookOpen size={14} style={{ color: tmpl.is_builtin ? 'var(--accent)' : 'var(--mute)', flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{tmpl.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--mute)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{tmpl.description}</div>
                </div>
                <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'var(--surface)', color: 'var(--mute)' }}>{tmpl.category}</span>
                {expandedId === tmpl.id ? <ChevronDown size={12} /> : <ChevronDown size={12} style={{ transform: 'rotate(-90deg)' }} />}
              </div>

              {expandedId === tmpl.id && (
                <div style={{ padding: '0 16px 12px', animation: 'floating-panel-appear 0.15s ease' }}>
                  {tmpl.sections.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 4 }}>{t('templateGallery.sections')}</div>
                      {tmpl.sections.map((s, i) => (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, padding: '2px 0' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.required ? 'var(--accent)' : 'var(--hairline)' }} />
                          <span>{s.title}</span>
                          {s.required && <span style={{ fontSize: 10, color: 'var(--accent)' }}>*</span>}
                        </div>
                      ))}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: 8 }}>
                    {onApply && (
                      <button
                        onClick={() => onApply(tmpl)}
                        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 12px', borderRadius: 6, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 12 }}
                      >
                        <Check size={12} />{t('templateGallery.apply')}
                      </button>
                    )}
                    {!tmpl.is_builtin && (
                      <button
                        onClick={() => handleDelete(tmpl.id)}
                        style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', borderRadius: 6, border: '1px solid rgba(239,68,68,0.3)', background: 'transparent', color: '#ef4444', cursor: 'pointer', fontSize: 12 }}
                      >
                        <Trash2 size={12} />{t('templateGallery.delete')}
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
