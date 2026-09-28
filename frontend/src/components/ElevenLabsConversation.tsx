import { useEffect, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import { Button } from "@/components/ui/button";

const ElevenLabsConversation = () => {
  const [message, setMessage] = useState("");

  const {
    conversation,
    status,
    isSpeaking,
    connect,
    disconnect,
    sendMessage,
  } = useConversation({
    // Optional initialization config (depending on your ElevenLabs setup)
    // e.g. modelId, voiceId, aiOptions, etc.
    // You can pass any supported options here.
  });

  useEffect(() => {
    console.log("[ElevenLabs] connection status:", status);
  }, [status]);

  useEffect(() => {
    console.log("[ElevenLabs] isSpeaking:", isSpeaking);
  }, [isSpeaking]);

  const handleConnect = async () => {
    try {
      await connect();
      console.log("[ElevenLabs] connect() called");
    } catch (error) {
      console.error("[ElevenLabs] connect failed:", error);
    }
  };

  const handleDisconnect = async () => {
    try {
      await disconnect();
      console.log("[ElevenLabs] disconnect() called");
    } catch (error) {
      console.error("[ElevenLabs] disconnect failed:", error);
    }
  };

  const handleSend = async () => {
    if (!message.trim()) return;
    try {
      await sendMessage(message);
      console.log("[ElevenLabs] sendMessage():", message);
      setMessage("");
    } catch (error) {
      console.error("[ElevenLabs] sendMessage failed:", error);
    }
  };

  const isConnected = status === "connected";

  return (
    <section className="mt-8 p-6 rounded-xl bg-background/80 border border-primary/20 max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold mb-3">ElevenLabs Conversation Demo</h2>
      <p className="text-sm text-muted-foreground mb-4">
        status: <strong>{status || "unknown"}</strong> | isSpeaking: <strong>{String(isSpeaking)}</strong>
      </p>

      <div className="flex gap-2 mb-4">
        <Button onClick={handleConnect} disabled={isConnected}>
          Connect
        </Button>
        <Button onClick={handleDisconnect} disabled={!isConnected}>
          Disconnect
        </Button>
      </div>

      <div className="flex gap-2">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="flex-1 rounded-lg border p-2"
          placeholder="Type a message..."
        />
        <Button onClick={handleSend} disabled={!isConnected || !message.trim()}>
          Send
        </Button>
      </div>

      <div className="mt-4 text-sm text-muted-foreground">
        <strong>Conversation length:</strong> {conversation?.messages?.length ?? 0}
      </div>
    </section>
  );
};

export default ElevenLabsConversation;
