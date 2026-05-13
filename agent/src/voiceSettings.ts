export type ReplyMode = "text" | "voice";

export interface VoiceSettings {
  replyMode: ReplyMode;
  preferredVoiceId?: string;
  callModeAvailable: boolean;
  activeCallSessionId?: string;
}

export const voiceSettings: VoiceSettings = {
  replyMode: "text",
  preferredVoiceId: process.env.TTS_VOICE_ID || undefined,
  callModeAvailable: true,
};

export function setVoiceMode(enabled: boolean) {
  voiceSettings.replyMode = enabled ? "voice" : "text";
}

export function isVoiceModeEnabled() {
  return voiceSettings.replyMode === "voice";
}

export function setPreferredVoice(voiceId: string) {
  voiceSettings.preferredVoiceId = voiceId;
}

export function getVoiceStatus() {
  return {
    replyMode: voiceSettings.replyMode,
    preferredVoiceId: voiceSettings.preferredVoiceId || null,
    callModeAvailable: voiceSettings.callModeAvailable,
    activeCallSessionId: voiceSettings.activeCallSessionId || null,
  };
}
