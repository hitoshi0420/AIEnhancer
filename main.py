"""AI 视频画质增强器 — 基于 Real-ESRGAN 超分辨率"""

import os
import time
import asyncio
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from upscaler import upscale_video, check_esrgan, UpscaleProgress
from helpers import format_time

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# 主题色定义
THEME = {
    "bg_primary": "#0f0f0f",
    "bg_secondary": "#1a1a1a",
    "bg_card": "#252525",
    "bg_input": "#2a2a2a",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "text_primary": "#e5e5e5",
    "text_secondary": "#a3a3a3",
    "text_muted": "#737373",
    "success": "#22c55e",
    "error": "#ef4444",
    "info": "#3b82f6",
    "progress_bg": "#333333",
}


class AIEnhancerApp(ctk.CTk):
    """AI 视频画质增强器主窗口"""

    def __init__(self):
        super().__init__()

        self.title("AI 视频画质增强器 — Real-ESRGAN")
        self.geometry("700x700")
        self.minsize(550, 500)
        self.configure(fg_color=THEME["bg_primary"])

        self._input_path = ""
        self._output_path = ""
        self._running = False
        self._keep_temp = False
        self._loop: asyncio.AbstractEventLoop = None
        self._start_time = 0.0
        self._total_frames = 0

        self._build_ui()
        self._check_tool()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """构建界面"""
        t = THEME

        # ====== 标题栏 ======
        header = ctk.CTkFrame(self, height=48, fg_color=t["bg_secondary"], corner_radius=0)
        header.pack(fill="x")

        ctk.CTkLabel(
            header, text="🎨 AI 视频画质增强器",
            text_color=t["accent"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            header, text="Real-ESRGAN 4x | Vulkan GPU 加速",
            text_color=t["text_muted"],
            font=ctk.CTkFont(size=11),
        ).pack(side="right", padx=20, pady=10)

        # ====== 文件选择区 ======
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(file_frame, text="输入视频", text_color=t["text_secondary"],
                     font=ctk.CTkFont(size=12)).pack(anchor="w")

        row1 = ctk.CTkFrame(file_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(4, 0))

        self.input_entry = ctk.CTkEntry(
            row1, height=34, fg_color=t["bg_input"],
            placeholder_text="选择要增强的视频文件...",
            font=ctk.CTkFont(size=12),
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            row1, text="选择文件", width=90, height=34,
            fg_color=t["bg_card"], text_color=t["text_primary"],
            font=ctk.CTkFont(size=12),
            command=self._pick_input,
        ).pack(side="right")

        # 拖拽提示
        ctk.CTkLabel(
            file_frame, text="支持 MP4 / MKV / AVI / FLV / WebM",
            text_color=t["text_muted"], font=ctk.CTkFont(size=10),
        ).pack(anchor="w", pady=(2, 0))

        # ====== 设置区 ======
        settings_frame = ctk.CTkFrame(self, fg_color=t["bg_secondary"], corner_radius=8)
        settings_frame.pack(fill="x", padx=20, pady=(12, 0))

        ctk.CTkLabel(
            settings_frame, text="增强设置",
            text_color=t["text_primary"], font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(12, 4))

        row_set = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row_set.pack(fill="x", padx=16, pady=(4, 12))

        # 缩放倍数
        scale_frame = ctk.CTkFrame(row_set, fg_color="transparent")
        scale_frame.pack(side="left", padx=(0, 24))

        ctk.CTkLabel(scale_frame, text="增强倍数", text_color=t["text_secondary"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        self.scale_var = ctk.StringVar(value="4")
        scale_row = ctk.CTkFrame(scale_frame, fg_color="transparent")
        scale_row.pack(pady=(4, 0))

        for val, text in [("4", "4x (推荐)"), ("2", "2x")]:
            rb = ctk.CTkRadioButton(
                scale_row, text=text, variable=self.scale_var, value=val,
                font=ctk.CTkFont(size=12), text_color=t["text_primary"],
                fg_color=t["accent"],
            )
            rb.pack(side="left", padx=(0, 16))

        # 模型选择
        model_frame = ctk.CTkFrame(row_set, fg_color="transparent")
        model_frame.pack(side="left")

        ctk.CTkLabel(model_frame, text="模型", text_color=t["text_secondary"],
                     font=ctk.CTkFont(size=11)).pack(anchor="w")

        self.model_combo = ctk.CTkComboBox(
            model_frame, width=200, height=30,
            values=["realesrgan-x4plus (通用)", "realesrgan-x4plus-anime (动漫)"],
            font=ctk.CTkFont(size=12),
            fg_color=t["bg_input"], button_color=t["accent"],
        )
        self.model_combo.set("realesrgan-x4plus (通用)")
        self.model_combo.pack(pady=(4, 0))

        # 保留临时文件
        self.keep_temp_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            settings_frame, text="保留临时文件（调试用）",
            variable=self.keep_temp_var,
            font=ctk.CTkFont(size=11), text_color=t["text_muted"],
            fg_color=t["accent"],
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # 输出位置
        ctk.CTkLabel(settings_frame, text="输出位置 (留空则保存在输入文件同目录)",
                     text_color=t["text_muted"], font=ctk.CTkFont(size=10),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # ====== 进度区 ======
        progress_frame = ctk.CTkFrame(self, fg_color=t["bg_secondary"], corner_radius=8)
        progress_frame.pack(fill="x", padx=20, pady=(12, 0))

        self.stage_label = ctk.CTkLabel(
            progress_frame, text="就绪 — 选择视频文件后开始",
            text_color=t["text_secondary"], font=ctk.CTkFont(size=12),
        )
        self.stage_label.pack(anchor="w", padx=16, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame, height=12,
            progress_color=t["accent"], fg_color=t["progress_bg"],
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 8))
        self.progress_bar.set(0)

        self.progress_detail = ctk.CTkLabel(
            progress_frame, text="",
            text_color=t["text_muted"], font=ctk.CTkFont(size=11),
        )
        self.progress_detail.pack(anchor="w", padx=16, pady=(0, 10))

        # ====== 日志区 ======
        log_frame = ctk.CTkFrame(self, fg_color=t["bg_secondary"], corner_radius=8)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        ctk.CTkLabel(
            log_frame, text="处理日志",
            text_color=t["text_secondary"], font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=16, pady=(8, 2))

        self.log_box = ctk.CTkTextbox(
            log_frame, height=120,
            fg_color=t["bg_card"], text_color=t["text_primary"],
            font=ctk.CTkFont(family="Consolas", size=11), wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(2, 8))
        self.log_box.configure(state="disabled")

        # ====== 按钮区 ======
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(12, 16))

        self.btn_start = ctk.CTkButton(
            btn_frame, text="🎨 开始增强", width=140, height=40,
            fg_color=t["accent"], text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_enhance,
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="取消", width=80, height=40,
            fg_color=t["bg_card"], text_color=t["text_secondary"],
            font=ctk.CTkFont(size=13),
            command=self._cancel,
        ).pack(side="left")

        # 打开输出目录
        self.btn_open = ctk.CTkButton(
            btn_frame, text="📂 打开输出目录", width=120, height=40,
            fg_color=t["bg_card"], text_color=t["text_primary"],
            font=ctk.CTkFont(size=12),
            command=self._open_output,
        )
        self.btn_open.pack(side="right")
        self.btn_open.configure(state="disabled")

    def _check_tool(self):
        """检查 Real-ESRGAN 工具是否可用"""
        if not check_esrgan():
            self._log("⚠ Real-ESRGAN 未找到，请确保 VideoSniffer 已安装")
            self.btn_start.configure(state="disabled")
        else:
            self._log("✅ Real-ESRGAN ncnn-vulkan 已就绪")

    def _log(self, msg: str):
        """写入日志"""
        self.log_box.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{timestamp}] {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _pick_input(self):
        """选择输入视频文件"""
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.avi *.flv *.webm *.mov *.m4v"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self._input_path = path
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, path)
            self._log(f"已选择: {os.path.basename(path)}")
            self._update_info()

    def _update_info(self):
        """显示视频信息"""
        if not self._input_path:
            return
        try:
            size_mb = os.path.getsize(self._input_path) / (1024 * 1024)
            self.stage_label.configure(
                text=f"视频: {os.path.basename(self._input_path)} ({size_mb:.1f} MB) — 就绪"
            )
        except Exception:
            pass

    def _start_enhance(self):
        """开始 AI 增强"""
        if self._running:
            return
        if not self._input_path:
            self._input_path = self.input_entry.get().strip()
        if not self._input_path or not os.path.exists(self._input_path):
            messagebox.showwarning("提示", "请先选择有效的视频文件")
            return
        if not check_esrgan():
            messagebox.showerror("错误", "Real-ESRGAN 未安装，无法启动")
            return

        self._running = True
        self._keep_temp = self.keep_temp_var.get()
        self._start_time = time.time()
        self.btn_start.configure(text="处理中...", state="disabled", fg_color=THEME["text_muted"])
        self.progress_bar.set(0)
        self._log("===== 开始 AI 画质增强 =====")

        scale = int(self.scale_var.get())
        model_raw = self.model_combo.get()
        model_name = "realesrgan-x4plus" if "通用" in model_raw else "realesrgan-x4plus-anime"
        self._log(f"倍数: {scale}x | 模型: {model_name}")

        input_path = self._input_path
        # 输出路径
        stem, ext = os.path.splitext(input_path)
        output_path = f"{stem}_{scale}x.mp4"

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                result = loop.run_until_complete(
                    upscale_video(input_path, output_path, scale=scale,
                                  on_progress=self._on_progress,
                                  keep_temp=self._keep_temp)
                )
                self.after(0, lambda: self._on_done(result))
            except Exception as e:
                import traceback
                err = f"{e}\n{traceback.format_exc()}"
                self.after(0, lambda e=err: self._on_done("", e))
            finally:
                loop.close()

        threading.Thread(target=_run, daemon=True).start()

    def _cancel(self):
        """取消操作"""
        if not self._running:
            return
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._log("⚠ 用户取消了操作")
        self._reset_ui()

    def _on_progress(self, p: UpscaleProgress):
        """进度回调（在工作线程中调用）"""
        self.after(0, lambda: self._update_progress(p))

    def _update_progress(self, p: UpscaleProgress):
        """更新进度 UI"""
        if p.error:
            self._log(f"❌ 错误: {p.error}")
            return
        stages = {"extracting": "拆帧中", "upscaling": "AI 超分中", "merging": "合成中", "done": "完成"}
        stage_text = stages.get(p.stage, p.stage)
        self.progress_bar.set(p.progress / 100)

        elapsed = time.time() - self._start_time if self._start_time else 0

        if p.stage == "upscaling" and p.total_frames > 0:
            self._total_frames = p.total_frames
            done = p.frame
            total = p.total_frames
            fps = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / fps if fps > 0 else 0
            self.stage_label.configure(
                text=f"🎨 {stage_text}: {done}/{total} 帧 ({p.progress:.0f}%)"
            )
            self.progress_detail.configure(
                text=f"速度: {fps:.1f} 帧/秒 | 耗时: {format_time(elapsed)} | 剩余: {format_time(eta)}"
            )
        else:
            self.stage_label.configure(text=f"🎨 {stage_text}: {p.progress:.0f}%")
            self.progress_detail.configure(text=f"耗时: {format_time(elapsed)}")

    def _on_done(self, output_path: str, error: str = ""):
        """增强完成"""
        self._running = False
        if error:
            self._log(f"❌ 增强失败: {error}")
            self.stage_label.configure(text="增强失败", require_redraw=False)
            self.progress_detail.configure(text=error[:200])
        else:
            elapsed = time.time() - self._start_time
            size_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
            self._log(f"✅ 增强完成: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
            self._log(f"总耗时: {format_time(elapsed)}")
            self.stage_label.configure(text=f"✅ 完成 — {os.path.basename(output_path)} ({size_mb:.1f} MB)")
            self.progress_detail.configure(text=f"总耗时: {format_time(elapsed)}")
            self.progress_bar.set(1)
            self.btn_open.configure(state="normal")
            self._output_path = output_path

        self.btn_start.configure(text="🎨 开始增强", state="normal", fg_color=THEME["accent"])

    def _reset_ui(self):
        """重置 UI 状态"""
        self.btn_start.configure(text="🎨 开始增强", state="normal", fg_color=THEME["accent"])
        self.progress_bar.set(0)
        self.stage_label.configure(text="就绪")
        self.progress_detail.configure(text="")

    def _open_output(self):
        """打开输出目录"""
        if self._output_path and os.path.exists(self._output_path):
            os.startfile(os.path.dirname(self._output_path))
        elif self._input_path:
            os.startfile(os.path.dirname(self._input_path))

    def _on_close(self):
        """关闭窗口"""
        self._running = False
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        self.destroy()


def main():
    app = AIEnhancerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
