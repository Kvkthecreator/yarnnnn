import Link from "next/link";

export default function LandingFooter() {
  return (
    <footer className="border-t border-border py-8 px-6">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Brand */}
        <div className="flex flex-col items-start gap-2">
          <div className="font-bold text-lg">YARNNN</div>
          <div className="flex gap-4 text-sm text-muted-foreground">
            <Link href="/privacy" className="hover:text-foreground transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-foreground transition-colors">
              Terms
            </Link>
          </div>
        </div>

        {/* Contact */}
        <div className="flex flex-col md:flex-row md:items-center gap-4 md:gap-12 text-sm">
          <div>
            <div className="font-medium mb-1">Office</div>
            <div className="text-muted-foreground">
              Donggyo-Ro 272-8 3F, Seoul, Korea
            </div>
          </div>
          <div>
            <div className="font-medium mb-1">Contact</div>
            <div className="text-muted-foreground">
              contactus@yarnnn.com
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
