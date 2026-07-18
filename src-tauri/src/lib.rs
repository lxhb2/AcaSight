//! AcaSight Tauri v2 entry point

mod commands;

use tauri::menu::{MenuBuilder, MenuItemBuilder, SubmenuBuilder};
use tauri::tray::TrayIconBuilder;
use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::GlobalShortcutExt;
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec![]),
        ))
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_window_state::Builder::new().build())
        .invoke_handler(tauri::generate_handler![
            commands::get_system_info,
            commands::open_file_in_system,
            commands::read_file_base64,
            commands::read_file_text,
            commands::write_file_base64,
            commands::write_file_text,
            commands::file_exists,
            commands::create_dir,
            commands::file_metadata
        ])
        .setup(|app| {
            // ── Application menu bar ──
            let about_item = MenuItemBuilder::with_id("about", "关于 AcaSight").build(app)?;
            let settings_item = MenuItemBuilder::with_id("settings", "设置...").build(app)?;
            let check_update_item = MenuItemBuilder::with_id("check_update", "检查更新...").build(app)?;
            let file_menu = SubmenuBuilder::new(app, "文件")
                .items(&[
                    &MenuItemBuilder::with_id("new_window", "新建窗口").build(app)?,
                    &MenuItemBuilder::with_id("close_window", "关闭窗口").build(app)?,
                ])
                .build()?;

            let edit_menu = SubmenuBuilder::new(app, "编辑")
                .items(&[
                    &MenuItemBuilder::with_id("undo", "撤销").build(app)?,
                    &MenuItemBuilder::with_id("redo", "重做").build(app)?,
                    &MenuItemBuilder::with_id("cut", "剪切").build(app)?,
                    &MenuItemBuilder::with_id("copy", "复制").build(app)?,
                    &MenuItemBuilder::with_id("paste", "粘贴").build(app)?,
                    &MenuItemBuilder::with_id("select_all", "全选").build(app)?,
                ])
                .build()?;

            let view_menu = SubmenuBuilder::new(app, "视图")
                .items(&[
                    &MenuItemBuilder::with_id("toggle_fullscreen", "全屏").build(app)?,
                    &MenuItemBuilder::with_id("toggle_devtools", "开发者工具").build(app)?,
                    &MenuItemBuilder::with_id("zoom_in", "放大").build(app)?,
                    &MenuItemBuilder::with_id("zoom_out", "缩小").build(app)?,
                    &MenuItemBuilder::with_id("zoom_reset", "重置缩放").build(app)?,
                ])
                .build()?;

            let help_menu = SubmenuBuilder::new(app, "帮助")
                .items(&[&about_item, &settings_item, &check_update_item])
                .build()?;

            let menu = MenuBuilder::new(app)
                .items(&[&file_menu, &edit_menu, &view_menu, &help_menu])
                .build()?;

            app.set_menu(menu)?;

            // ── Menu event handler ──
            app.on_menu_event(move |app_handle, event| {
                match event.id().as_ref() {
                    "new_window" => {
                        // 前端处理：打开新面板
                        let _ = app_handle.emit("menu-action", "new_window");
                    }
                    "close_window" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.close();
                        }
                    }
                    "undo" | "redo" | "cut" | "copy" | "paste" | "select_all" => {
                        // 编辑操作由 WebView 内部处理，无需额外逻辑
                    }
                    "toggle_fullscreen" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let is_fullscreen = window.is_fullscreen().unwrap_or(false);
                            let _ = window.set_fullscreen(!is_fullscreen);
                        }
                    }
                    "toggle_devtools" => {
                        if let Some(window) = app_handle.get_webview_window("main") {
                            // devtools 仅在 debug 模式或显式启用时可用
                            #[cfg(debug_assertions)]
                            {
                                window.open_devtools();
                            }
                        }
                    }
                    "zoom_in" => {
                        let _ = app_handle.emit("menu-action", "zoom_in");
                    }
                    "zoom_out" => {
                        let _ = app_handle.emit("menu-action", "zoom_out");
                    }
                    "zoom_reset" => {
                        let _ = app_handle.emit("menu-action", "zoom_reset");
                    }
                    "about" => {
                        let _ = app_handle.emit("menu-action", "about");
                    }
                    "settings" => {
                        let _ = app_handle.emit("menu-action", "settings");
                    }
                    "check_update" => {
                        let _ = app_handle.emit("menu-action", "check_update");
                    }
                    _ => {}
                }
            });

            // ── Global shortcuts ──
            let shortcut_mgr = app.global_shortcut();

            // Alt+Shift+A: 显示/隐藏主窗口
            let toggle_shortcut = Shortcut::new(Some(Modifiers::ALT | Modifiers::SHIFT), Code::KeyA);
            shortcut_mgr.on_shortcut(toggle_shortcut, move |app_handle, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    if let Some(window) = app_handle.get_webview_window("main") {
                        if window.is_visible().unwrap_or(false) {
                            let _ = window.hide();
                        } else {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                }
            })?;

            // Alt+Shift+S: 快速保存当前文档
            let save_shortcut = Shortcut::new(Some(Modifiers::ALT | Modifiers::SHIFT), Code::KeyS);
            shortcut_mgr.on_shortcut(save_shortcut, move |app_handle, _shortcut, event| {
                if event.state == ShortcutState::Pressed {
                    let _ = app_handle.emit("menu-action", "quick_save");
                }
            })?;

            // ── System tray menu ──
            let show_item = MenuItemBuilder::with_id("show", "显示 AcaSight").build(app)?;
            let quit_item = MenuItemBuilder::with_id("quit", "退出").build(app)?;
            let tray_menu = MenuBuilder::new(app)
                .items(&[&show_item, &quit_item])
                .build()?;

            let icon = tauri::image::Image::from_bytes(include_bytes!("../icons/icon.png"))
                .unwrap_or_else(|_| tauri::image::Image::from_bytes(include_bytes!("../icons/32x32.png")).unwrap());

            let _tray = TrayIconBuilder::with_id("main")
                .icon(icon)
                .menu(&tray_menu)
                .tooltip("AcaSight 学术视界")
                .on_menu_event(move |app_handle, event| {
                    match event.id().as_ref() {
                        "show" => {
                            if let Some(window) = app_handle.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            app_handle.exit(0);
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click { .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            // ── Window close → minimize to tray ──
            if let Some(window) = app.get_webview_window("main") {
                let win = window.clone();
                window.on_window_event(move |event| {
                    if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                        api.prevent_close();
                        let _ = win.hide();
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running AcaSight");
}
