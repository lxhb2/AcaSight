//! Tauri commands — custom backend logic exposed to the frontend

use serde::Serialize;
use base64::Engine;

/// Get system information
#[tauri::command]
pub fn get_system_info() -> SystemInfo {
    SystemInfo {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    }
}

/// Open a file in the system default application
#[tauri::command]
pub async fn open_file_in_system(path: String) -> Result<(), String> {
    open::that(&path).map_err(|e| e.to_string())
}

/// Read a file and return its content as base64 (bypasses FS plugin scope restrictions)
#[tauri::command]
pub fn read_file_base64(path: String) -> Result<String, String> {
    let data = std::fs::read(&path).map_err(|e| format!("读取文件失败: {}", e))?;
    Ok(base64::engine::general_purpose::STANDARD.encode(&data))
}

/// Read a file and return its content as text (UTF-8)
#[tauri::command]
pub fn read_file_text(path: String) -> Result<String, String> {
    let data = std::fs::read(&path).map_err(|e| format!("读取文件失败: {}", e))?;
    String::from_utf8(data).map_err(|e| format!("文件不是有效的UTF-8文本: {}", e))
}

/// Write base64 content to a file (bypasses FS plugin scope restrictions)
#[tauri::command]
pub fn write_file_base64(path: String, content_b64: String) -> Result<(), String> {
    let data = base64::engine::general_purpose::STANDARD
        .decode(&content_b64)
        .map_err(|e| format!("Base64解码失败: {}", e))?;
    std::fs::write(&path, &data).map_err(|e| format!("写入文件失败: {}", e))
}

/// Write text content to a file (UTF-8)
#[tauri::command]
pub fn write_file_text(path: String, content: String) -> Result<(), String> {
    std::fs::write(&path, &content).map_err(|e| format!("写入文件失败: {}", e))
}

/// Check if a file or directory exists
#[tauri::command]
pub fn file_exists(path: String) -> bool {
    std::path::Path::new(&path).exists()
}

/// Create directory (recursive)
#[tauri::command]
pub fn create_dir(path: String) -> Result<(), String> {
    std::fs::create_dir_all(&path).map_err(|e| format!("创建目录失败: {}", e))
}

/// Get file metadata (size, mtime, is_dir)
#[tauri::command]
pub fn file_metadata(path: String) -> Result<FileMetadata, String> {
    let meta = std::fs::metadata(&path).map_err(|e| format!("获取元数据失败: {}", e))?;
    let mtime = meta.modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_secs())
        .unwrap_or(0);
    Ok(FileMetadata {
        size: meta.len(),
        is_dir: meta.is_dir(),
        is_file: meta.is_file(),
        mtime,
    })
}

#[derive(Serialize)]
pub struct FileMetadata {
    pub size: u64,
    pub is_dir: bool,
    pub is_file: bool,
    pub mtime: u64,
}

#[derive(Serialize)]
pub struct SystemInfo {
    pub os: String,
    pub arch: String,
    pub version: String,
}
