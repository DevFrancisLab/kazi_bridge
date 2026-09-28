import { Briefcase, ShieldCheck, Brain, Zap } from "lucide-react";

const features = [
  {
    icon: Briefcase,
    title: "Post Jobs & Receive Bids",
    description:
      "Create detailed job listings and receive competitive bids from qualified freelancers within minutes.",
  },
  {
    icon: ShieldCheck,
    title: "Secure Payments",
    description:
      "Pay with M-Pesa, crypto, or traditional methods — all protected by escrow until work is approved.",
  },
  {
    icon: Brain,
    title: "Smart Task Priority & Burnout Alerts",
    description:
      "AI monitors workload patterns and flags burnout risks so your team stays productive and healthy.",
  },
  {
    icon: Zap,
    title: "AI-Powered Matching",
    description:
      "Our intelligent matching engine connects you with freelancers whose skills perfectly fit your project.",
  },
];

const FeaturesSection = () => {
  return (
    <section id="features" className="py-24 bg-background">
      <div className="container mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Everything you need to get work done
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            A modern toolkit designed for seamless freelancer collaboration.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group bg-card rounded-xl p-7 shadow-card hover:shadow-card-hover transition-all duration-300 hover:-translate-y-1 border border-border/50"
            >
              <div className="w-11 h-11 rounded-lg bg-secondary flex items-center justify-center mb-5 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <feature.icon className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-semibold text-card-foreground mb-2">
                {feature.title}
              </h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;
