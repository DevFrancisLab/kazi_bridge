import { useState, useEffect } from "react";
import heroBg from "@/assets/hero-bg.jpg";

const HeroSection = () => {
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
          <p className="max-w-xl text-lg md:text-xl text-primary-foreground/90 leading-relaxed">
            Global businesses hire African freelancers on KaziBridge. Freelancers receive their earnings in their own country.
          </p>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
