import os
from typing import List, Dict

class Analyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _offline_diarize_and_summarize(self, segments: List[Dict]) -> tuple[str, str, str, str]:
        """
        100% offline rule-based analyzer for role alignment, summary, and requirements.
        Returns a tuple: (txt_content, md_conversation, md_summary, md_requirements)
        """
        txt_lines = []
        md_conversation_lines = []

        # Simple rule-based alignment: Alternate Speaker A and B on long pauses
        # For simplicity in this demo, just assign based on index
        # Real logic might look at silence gaps between segments

        speaker_map = {0: "发言人A", 1: "发言人B"}
        current_speaker_idx = 0

        summary_points = []
        requirements = []

        last_end = 0.0

        for i, seg in enumerate(segments):
            start = seg.get('start', 0.0)
            end = seg.get('end', 0.0)
            text = seg.get('text', '').strip()

            # If gap > 2 seconds, assume speaker change
            if start - last_end > 2.0:
                current_speaker_idx = (current_speaker_idx + 1) % 2

            speaker = speaker_map[current_speaker_idx]

            # Formatting timestamps
            start_str = self._format_time(start)
            end_str = self._format_time(end)

            line_str = f"[{start_str} --> {end_str}] {speaker}: {text}"

            txt_lines.append(f"{text}")
            md_conversation_lines.append(f"**{speaker}** ({start_str} - {end_str}): {text}")

            # Simple keyword extraction for summary and requirements
            if "需求" in text or "需要" in text or "要" in text:
                requirements.append(f"- {text}")
            if "总结" in text or "重点" in text:
                summary_points.append(f"- {text}")

            last_end = end

        txt_content = "\n".join(txt_lines)
        md_conversation = "# 会议对话记录\n\n" + "\n\n".join(md_conversation_lines)

        # If no explicit points found, just add generic ones
        if not summary_points:
            summary_points.append("- 讨论了相关项目的进展与细节。")
        if not requirements:
            requirements.append("- 暂无明确的行动项或需求。")

        md_summary = "# 会议纪要\n\n## 核心内容提取\n" + "\n".join(summary_points)
        md_requirements = "# 客户需求清单\n\n## 待办与需求\n" + "\n".join(requirements)

        return txt_content, md_conversation, md_summary, md_requirements

    def analyze(self, segments: List[Dict]) -> tuple[str, str, str, str]:
        """
        Main analysis method. Tries LLM if API key is provided, falls back to offline.
        """
        if self.api_key:
            try:
                # Mock LLM API call, falls back if it fails
                # In a real app, you would use requests/openai to call the API
                # and raise an exception if it times out
                raise Exception("LLM API connection failed (Mock)")
            except Exception as e:
                print(f"API请求失败，自动无缝降级回离线模式: {e}")

        # Fallback to offline
        return self._offline_diarize_and_summarize(segments)

    def _format_time(self, seconds: float) -> str:
        """Format seconds into HH:MM:SS"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
