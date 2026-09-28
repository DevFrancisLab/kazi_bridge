import { Link } from "react-router-dom";
import logo from "@/assets/kazibridgelogo.png";

type BrandLogoProps = {
  size?: "sm" | "md" | "lg";
  showWordmark?: boolean;
  wordmarkClassName?: string;
  className?: string;
  to?: string;
};

const frames = {
  sm: "h-8 w-[3.7rem]",
  md: "h-10 w-[4.6rem]",
  lg: "h-14 w-[6.45rem]",
};

const wordmarks = {
  sm: "text-base",
  md: "text-xl",
  lg: "text-2xl",
};

const BrandLogo = ({
  size = "md",
  showWordmark = true,
  wordmarkClassName = "text-slate-900",
  className = "",
  to,
}: BrandLogoProps) => {
  const content = (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span className={`relative inline-block shrink-0 overflow-hidden rounded-md ${frames[size]}`}>
        <img
          src={logo}
          alt={showWordmark ? "" : "KaziBridge"}
          className="absolute left-1/2 top-1/2 h-[255%] w-auto max-w-none -translate-x-1/2 -translate-y-1/2"
        />
      </span>
      {showWordmark ? (
        <span className={`font-bold tracking-tight ${wordmarks[size]} ${wordmarkClassName}`}>
          KaziBridge
        </span>
      ) : null}
    </span>
  );

  if (to) {
    return (
      <Link to={to} className="inline-flex rounded-md" aria-label="KaziBridge home">
        {content}
      </Link>
    );
  }

  return content;
};

export default BrandLogo;
