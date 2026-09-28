const Footer = () => {
  return (
    <footer className="bg-footer py-10">
      <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
        <p className="text-sm text-footer-foreground">
          © 2026 KaziBridge. All rights reserved.
        </p>
        <div className="flex gap-6">
          {["Privacy", "Terms", "Contact"].map((link) => (
            <a
              key={link}
              href="#"
              className="text-sm text-footer-foreground hover:text-foreground transition-colors"
            >
              {link}
            </a>
          ))}
        </div>
      </div>
    </footer>
  );
};

export default Footer;
