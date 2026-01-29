import Link from "next/link";
import Image from "next/image";

interface LandingHeaderProps {
  inverted?: boolean;
}

export default function LandingHeader({ inverted }: LandingHeaderProps) {
  return (
    <header
      className={`w-full py-4 px-6 flex justify-between items-center border-b ${
        inverted ? "border-background/10" : "border-border"
      }`}
    >
      <Link href="/" className="flex items-center gap-2">
        <Image
          src="/assets/logos/circleonly_yarnnn.png"
          alt="yarnnn"
          width={32}
          height={32}
          className={inverted ? "invert" : ""}
        />
        <span className="text-xl font-brand">yarnnn</span>
      </Link>
      <nav className="flex items-center gap-6">
        <Link
          href="/about"
          className={`transition-colors ${
            inverted
              ? "text-background/60 hover:text-background"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          About
        </Link>
        <Link
          href="/auth/login"
          className={`px-4 py-2 transition-colors ${
            inverted
              ? "bg-background text-foreground hover:bg-background/90"
              : "bg-primary text-primary-foreground hover:bg-primary/90"
          }`}
        >
          Sign In
        </Link>
      </nav>
    </header>
  );
}
