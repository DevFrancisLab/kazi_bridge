import { useState, useEffect } from "react";
import { Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import heroBg from "@/assets/hero-bg.jpg";

const HeroSection = () => {
  const [query, setQuery] = useState("");
  const [displayedText, setDisplayedText] = useState("");
  const [showCursor, setShowCursor] = useState(true);
  const [isTypingComplete, setIsTypingComplete] = useState(false);
  const fullText = "Hire Top Freelancers, Faster";

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
        <div className="max-w-xl animate-fade-up">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight text-primary-foreground mb-6">
            {displayedText}
            <span className={`inline-block w-1 h-12 bg-primary-foreground ml-1 ${showCursor ? 'opacity-100' : 'opacity-0'} transition-opacity duration-100`}></span>
          </h1>
          <p className="text-lg md:text-xl text-primary-foreground/80 mb-10 leading-relaxed">
            Tell us your needs and our AI agent will connect you with the right
            talent instantly.
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
