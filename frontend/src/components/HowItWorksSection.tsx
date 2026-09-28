const steps = [
  {
    number: "01",
    title: "Post Your Job",
    description: "Describe what you need and set your budget. It only takes a minute.",
  },
  {
    number: "02",
    title: "Receive Bids or AI Matches",
    description: "Get proposals from freelancers or let our AI find the perfect match.",
  },
  {
    number: "03",
    title: "Pay Securely & Get Work Done",
    description: "Funds are held in escrow and released when you approve the deliverables.",
  },
];

const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-24 bg-secondary">
      <div className="container mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            How It Works
          </h2>
          <p className="text-muted-foreground text-lg">
            Three simple steps to getting your project done.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 max-w-4xl mx-auto">
          {steps.map((step, i) => (
            <div key={step.number} className="text-center">
              <div className="text-5xl font-bold text-border mb-4">
                {step.number}
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                {step.title}
              </h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                {step.description}
              </p>
              {i < steps.length - 1 && (
                <div className="hidden md:block absolute" />
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
