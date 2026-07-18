/**
 * Tauri API Adapter — 统一浏览器/Tauri环境
 * 在Tauri桌面端使用原生API，在浏览器中回退到Web API
 */

// Detect if running in Tauri
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

// Lazy-loaded Tauri APIs
let tauriFs: typeof import('@tauri-apps/plugin-fs') | null = null;
let tauriDialog: typeof import('@tauri-apps/plugin-dialog') | null = null;
let tauriShell: typeof import('@tauri-apps/plugin-shell') | null = null;
let tauriUpdater: typeof import('@tauri-apps/plugin-updater') | null = null;
let tauriProcess: typeof import('@tauri-apps/plugin-process') | null = null;

async function loadTauriApis() {
  if (!isTauri()) return;
  if (!tauriFs) {
    tauriFs = await import('@tauri-apps/plugin-fs');
    tauriDialog = await import('@tauri-apps/plugin-dialog');
    tauriShell = await import('@tauri-apps/plugin-shell');
    tauriUpdater = await import('@tauri-apps/plugin-updater');
    tauriProcess = await import('@tauri-apps/plugin-process');
  }
}

/* ── File System ── */

export interface FileFilter {
  name: string;
  extensions: string[];
}

export interface OpenFileOptions {
  multiple?: boolean;
  filters?: FileFilter[];
  title?: string;
}

export interface SaveFileOptions {
  filters?: FileFilter[];
  title?: string;
  defaultPath?: string;
}

/**
 * Open file dialog and read file content
 * Uses Tauri invoke commands to bypass FS plugin scope restrictions
 */
export async function openFile(options?: OpenFileOptions): Promise<Array<{ name: string; path: string; content: Uint8Array }>> {
  await loadTauriApis();

  if (isTauri() && tauriDialog) {
    const selected = await tauriDialog.open({
      multiple: options?.multiple ?? false,
      filters: options?.filters,
      title: options?.title,
    });

    if (!selected) return [];

    const paths = Array.isArray(selected) ? selected : [selected];
    const results = [];

    const { invoke } = await import('@tauri-apps/api/core');

    for (const filePath of paths) {
      try {
        // 使用 Rust 命令读取文件，绕过 FS 插件 scope 限制
        const base64Content = await invoke<string>('read_file_base64', { path: filePath });
        const binary = atob(base64Content);
        const content = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) content[i] = binary.charCodeAt(i);
        const name = filePath.split(/[/\\]/).pop() || 'unknown';
        results.push({ name, path: filePath, content });
      } catch (err) {
        console.error(`读取文件失败: ${filePath}`, err);
      }
    }

    return results;
  }

  // Browser fallback: use input[type=file]
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.multiple = options?.multiple ?? false;
    if (options?.filters) {
      input.accept = options.filters.map(f => f.extensions.map(e => `.${e}`).join(',')).join(',');
    }

    input.onchange = async () => {
      const files = input.files;
      if (!files) { resolve([]); return; }

      const results = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const buffer = await file.arrayBuffer();
        results.push({
          name: file.name,
          path: file.name,
          content: new Uint8Array(buffer),
        });
      }
      resolve(results);
    };

    input.click();
  });
}

/**
 * Save file dialog and write content
 * Uses Tauri invoke commands to bypass FS plugin scope restrictions
 */
export async function saveFile(content: Uint8Array | string, options?: SaveFileOptions): Promise<string | null> {
  await loadTauriApis();

  if (isTauri() && tauriDialog) {
    const filePath = await tauriDialog.save({
      filters: options?.filters,
      title: options?.title,
      defaultPath: options?.defaultPath,
    });

    if (!filePath) return null;

    const { invoke } = await import('@tauri-apps/api/core');

    if (typeof content === 'string') {
      await invoke('write_file_text', { path: filePath, content });
    } else {
      // Uint8Array → base64 → Rust write_file_base64
      let binary = '';
      for (let i = 0; i < content.length; i++) {
        binary += String.fromCharCode(content[i]);
      }
      const base64 = btoa(binary);
      await invoke('write_file_base64', { path: filePath, contentB64: base64 });
    }
    return filePath;
  }

  // Browser fallback: download via blob
  const blob = typeof content === 'string'
    ? new Blob([content], { type: 'text/plain' })
    : new Blob([content as BlobPart]);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = options?.defaultPath || 'download';
  a.click();
  URL.revokeObjectURL(url);
  return options?.defaultPath || null;
}

/**
 * Read file from path (Tauri only, no browser fallback)
 * Uses Tauri invoke commands to bypass FS plugin scope restrictions
 */
export async function readFile(path: string): Promise<Uint8Array> {
  await loadTauriApis();
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    const base64Content = await invoke<string>('read_file_base64', { path });
    const binary = atob(base64Content);
    const content = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) content[i] = binary.charCodeAt(i);
    return content;
  }
  throw new Error('readFile requires Tauri environment');
}

/**
 * Write file to path (Tauri only)
 * Uses Tauri invoke commands to bypass FS plugin scope restrictions
 */
export async function writeFile(path: string, content: Uint8Array | string): Promise<void> {
  await loadTauriApis();
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    if (typeof content === 'string') {
      await invoke('write_file_text', { path, content });
    } else {
      let binary = '';
      for (let i = 0; i < content.length; i++) {
        binary += String.fromCharCode(content[i]);
      }
      const base64 = btoa(binary);
      await invoke('write_file_base64', { path, contentB64: base64 });
    }
    return;
  }
  throw new Error('writeFile requires Tauri environment');
}

/**
 * Check if file exists
 * Uses Tauri invoke command to bypass FS plugin scope restrictions
 */
export async function fileExists(path: string): Promise<boolean> {
  await loadTauriApis();
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    return invoke<boolean>('file_exists', { path });
  }
  return false;
}

/**
 * Create directory
 * Uses Tauri invoke command to bypass FS plugin scope restrictions
 */
export async function createDir(path: string): Promise<void> {
  await loadTauriApis();
  if (isTauri()) {
    const { invoke } = await import('@tauri-apps/api/core');
    await invoke('create_dir', { path });
    return;
  }
  throw new Error('createDir requires Tauri environment');
}

/* ── Text File Helpers ── */

/**
 * Open file dialog and read as text
 */
export async function openTextFile(options?: OpenFileOptions): Promise<Array<{ name: string; path: string; content: string }>> {
  const files = await openFile(options);
  const decoder = new TextDecoder('utf-8');
  return files.map(f => ({
    name: f.name,
    path: f.path,
    content: decoder.decode(f.content),
  }));
}

/* ── Shell ── */

/**
 * Open URL or file in system default application
 */
export async function openInSystem(path: string): Promise<void> {
  await loadTauriApis();
  if (isTauri() && tauriShell) {
    await tauriShell.open(path);
    return;
  }
  // Browser fallback
  window.open(path, '_blank');
}

/* ── Updater ── */

export interface UpdateInfo {
  available: boolean;
  version?: string;
  date?: string;
  body?: string;
}

/**
 * Check for app updates
 */
export async function checkForUpdate(): Promise<UpdateInfo> {
  await loadTauriApis();
  if (isTauri() && tauriUpdater) {
    try {
      const update = await tauriUpdater.check();
      if (update) {
        return {
          available: true,
          version: update.version,
          date: update.date,
          body: update.body,
        };
      }
      return { available: false };
    } catch {
      return { available: false };
    }
  }
  return { available: false };
}

/**
 * Install available update
 */
export async function installUpdate(): Promise<void> {
  await loadTauriApis();
  if (isTauri() && tauriUpdater) {
    const update = await tauriUpdater.check();
    if (update) {
      await update.downloadAndInstall();
    }
  }
}

/* ── Process ── */

/**
 * Restart the app
 */
export async function restartApp(): Promise<void> {
  await loadTauriApis();
  if (isTauri() && tauriProcess) {
    tauriProcess.relaunch();
    return;
  }
  window.location.reload();
}

/**
 * Get app version
 */
export function getAppVersion(): string {
  return '3.0.0';
}

/* ── Window ── */

/**
 * Minimize window to tray (Tauri only)
 */
export async function minimizeToTray(): Promise<void> {
  if (!isTauri()) return;
  const { getCurrentWindow } = await import('@tauri-apps/api/window');
  const window = getCurrentWindow();
  await window.hide();
}

/**
 * Set window title
 */
export async function setWindowTitle(title: string): Promise<void> {
  if (!isTauri()) {
    document.title = title;
    return;
  }
  const { getCurrentWindow } = await import('@tauri-apps/api/window');
  const window = getCurrentWindow();
  await window.setTitle(title);
}

/* ── Menu Actions ── */

export type MenuAction =
  | 'new_window'
  | 'zoom_in'
  | 'zoom_out'
  | 'zoom_reset'
  | 'about'
  | 'settings'
  | 'check_update'
  | 'quick_save';

/**
 * Listen for native menu bar actions (Tauri only)
 */
export async function onMenuAction(callback: (action: MenuAction) => void): Promise<(() => void) | null> {
  if (!isTauri()) return null;

  const { listen } = await import('@tauri-apps/api/event');
  const unlisten = await listen<string>('menu-action', (event) => {
    callback(event.payload as MenuAction);
  });

  return unlisten;
}

/* ── Drag & Drop ── */

export interface FileDropEvent {
  paths: string[];
  position: { x: number; y: number };
}

/**
 * Listen for file drop events (Tauri only)
 */
export async function onFileDrop(callback: (event: FileDropEvent) => void): Promise<(() => void) | null> {
  if (!isTauri()) return null;

  const { getCurrentWindow } = await import('@tauri-apps/api/window');
  const window = getCurrentWindow();

  const unlisten = await window.onDragDropEvent((event) => {
    if (event.payload.type === 'drop') {
      callback({
        paths: event.payload.paths,
        position: event.payload.position,
      });
    }
  });

  return unlisten;
}
