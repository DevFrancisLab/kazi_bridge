import { Briefcase, ShieldCheck, Wallet, Zap } from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "AI-Powered Matching",
    description:
      "Find freelancers whose skills match your project and get the right talent faster.",
  },
  {
    icon: ShieldCheck,
    title: "Cross-Border Payments",
    description:
      "Pay freelancers across East Africa without managing separate payment processes for each country.",
  },
  {
    icon: Wallet,
    title: "Local Freelancer Payouts",
    description:
      "Freelancers receive their earnings through local payment methods in their country.",
  },
  {
    icon: Briefcase,
    title: "Jobs & Bids",
    description:
      "Post projects, receive bids, and manage your work from one place.",
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
