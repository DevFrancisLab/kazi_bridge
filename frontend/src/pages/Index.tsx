import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import ElevenLabsConversation from "@/components/ElevenLabsConversation";
import FeaturesSection from "@/components/FeaturesSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <ElevenLabsConversation />
      <FeaturesSection />
      <HowItWorksSection />
      <Footer />
    </div>
  );
};

export default Index;
