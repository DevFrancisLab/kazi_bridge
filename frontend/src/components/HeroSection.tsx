import { useState, useEffect } from "react";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroBg from "@/assets/hero-bg.jpg";

const HeroSection = () => {
  const [query, setQuery] = useState("");
  const [displayedText, setDisplayedText] = useState("");
  const [showCursor, setShowCursor] = useState(true);
  const [isTypingComplete, setIsTypingComplete] = useState(false);
  const fullText = "Hire Anywhere. Pay Locally.";
  const firstLine = "Hire Anywhere.";

  useEffect(() => {
    let index = 0;
    const typeWriter = () => {
      if (index < fullText.length) {
        setDisplayedText(fullText.slice(0, index + 1));
        index++;
        setTimeout(typeWriter, 100);
      } else {
        setIsTypingComplete(true);
      }
    };
    typeWriter();
  }, []);

  useEffect(() => {
    if (isTypingComplete) {
      let blinkCount = 0;
      const blinkInterval = setInterval(() => {
        setShowCursor(prev => !prev);
        blinkCount++;
        if (blinkCount >= 6) { // 3 full blinks (on-off cycles)
          setShowCursor(false);
          clearInterval(blinkInterval);
        }
      }, 500);
      return () => clearInterval(blinkInterval);
    }
  }, [isTypingComplete]);

  const handleSubmit = () => {
    if (query.trim()) {
      console.log("AI Query:", query);
    }
  };

  const handleVoice = () => {
    console.log("Voice input triggered (placeholder)");
  };

  return (
    <section
      className="relative h-screen flex items-center"
      style={{
        backgroundImage: `url(${heroBg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }}
    >
      {/* Dark overlay: reduced opacity for improved readability */}
      <div className="absolute inset-0 bg-foreground/20" />

      <div className="relative z-10 container mx-auto px-6 md:px-12 lg:px-16">
        <div className="max-w-3xl animate-fade-up">
          <h1 className="text-4xl md:text-5xl font-bold leading-tight text-primary-foreground mb-6">
            <span className="block">
              {displayedText.slice(0, firstLine.length)}
              {displayedText.length <= firstLine.length && (
                <span className={`inline-block w-1 h-10 md:h-12 bg-primary-foreground ml-1 align-middle ${showCursor ? "opacity-100" : "opacity-0"} transition-opacity duration-100`} />
              )}
            </span>
            {displayedText.length > firstLine.length && (
              <span className="block">
                {displayedText.slice(firstLine.length + 1)}
                <span className={`inline-block w-1 h-10 md:h-12 bg-primary-foreground ml-1 align-middle ${showCursor ? "opacity-100" : "opacity-0"} transition-opacity duration-100`} />
              </span>
            )}
          </h1>
          <p className="max-w-2xl text-lg md:text-xl text-primary-foreground/80 mb-10 leading-relaxed">
            KaziBridge connects global businesses with African talent and helps freelancers receive their earnings locally.
          </p>

          {/* AI Input */}
          <div className="flex items-center gap-2 bg-background rounded-xl shadow-card-hover p-2 max-w-lg">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              placeholder="Tell us your needs..."
              className="flex-1 bg-transparent px-4 py-3 text-foreground placeholder:text-muted-foreground outline-none text-base"
            />
            <button
              onClick={handleVoice}
              className="p-2.5 rounded-lg text-muted-foreground hover:text-foreground transition-colors hover:bg-accent"
              aria-label="Voice input"
            >
              <Mic className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
