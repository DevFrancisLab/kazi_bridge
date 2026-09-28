import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

const navLinks = ["Features", "How It Works", "Pricing", "Contact"];

const Navbar = () => {
  const [scrolled, setScrolled] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-background/95 backdrop-blur shadow-card"
          : "bg-transparent"
      }`}
    >
      <div className="container mx-auto flex items-center justify-between py-4 px-6">
        <a href="#" className={`text-xl font-bold tracking-tight transition-colors ${scrolled ? "text-foreground" : "text-primary-foreground"}`}>
          KaziBridge
        </a>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replace(/\s+/g, "-")}`}
              className={`text-sm font-medium transition-colors hover:opacity-80 ${
                scrolled ? "text-foreground" : "text-primary-foreground"
              }`}
            >
              {link}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/login")}
            className={`text-sm font-medium transition-colors hover:opacity-80 ${
              scrolled ? "text-foreground" : "text-primary-foreground"
            }`}
          >
            Login
          </button>
          <Button size="sm" className="rounded-lg" onClick={() => navigate("/signup")}>
            Sign Up
          </Button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
