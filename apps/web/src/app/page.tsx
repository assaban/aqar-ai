import Link from "next/link";

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-aqar-600 via-aqar-500 to-aqar-400">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTTAgMCBMNjAgNjAgTTYwIDAgTDAgNjAiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLW9wYWNpdHk9IjAuMDUiIHN0cm9rZS13aWR0aD0iMSIvPjwvcGF0dGVybj48L2RlZnM+PHJlY3QgZmlsbD0idXJsKCNnKSIgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIvPjwvc3ZnPg==')] opacity-50" />

        <div className="relative mx-auto max-w-4xl px-4 py-20 text-center sm:py-28">
          <h1 className="mb-4 text-4xl font-bold text-white sm:text-5xl lg:text-6xl">
            Find your property in{" "}
            <span className="text-aqar-100">Tangier</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-aqar-100/90">
            The first AI-powered real estate portal. We automatically analyze
            YouTube video tours from real estate agents to extract key property
            data from spoken Arabic and Darija.
          </p>

          {/* Search bar */}
          <form
            action="/search"
            method="GET"
            className="mx-auto flex max-w-xl overflow-hidden rounded-xl bg-white shadow-2xl shadow-aqar-800/20"
          >
            <input
              name="q"
              type="text"
              placeholder="Search: apartment Iberia, villa Marshan..."
              className="flex-1 px-5 py-4 text-sand-800 placeholder:text-sand-400 focus:outline-none"
            />
            <button
              type="submit"
              className="bg-aqar-500 px-6 py-4 font-semibold text-white transition-colors hover:bg-aqar-600"
            >
              Search
            </button>
          </form>

          {/* Quick filters */}
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {[
              { label: "Apartments", href: "/search?property_type=apartment" },
              { label: "Villas", href: "/search?property_type=villa" },
              { label: "Land", href: "/search?property_type=land" },
              { label: "For Rent", href: "/search?listing_type=rent" },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-full border border-white/30 px-4 py-1.5 text-sm text-white transition-colors hover:bg-white/20"
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:py-20">
        <h2 className="mb-12 text-center text-2xl font-bold text-sand-900 sm:text-3xl">
          How it works
        </h2>

        <div className="grid gap-8 sm:grid-cols-3">
          {[
            {
              icon: "📹",
              title: "Video Analysis",
              desc: "We scan YouTube channels of real estate agents in the Tangier-Tetouan region.",
            },
            {
              icon: "🤖",
              title: "AI Extraction",
              desc: "AI transcribes Darija/Arabic speech and extracts price, area, rooms, and location.",
            },
            {
              icon: "🗺️",
              title: "Searchable Portal",
              desc: "Search, filter, and locate properties on an interactive map.",
            },
          ].map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-sand-200 bg-white p-6 text-center transition-shadow hover:shadow-lg"
            >
              <div className="mb-4 text-4xl">{feature.icon}</div>
              <h3 className="mb-2 text-lg font-semibold text-sand-900">
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed text-sand-500">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-sand-100 py-12 text-center">
        <h2 className="mb-4 text-xl font-semibold text-sand-800">
          Ready to explore?
        </h2>
        <Link
          href="/search"
          className="inline-flex rounded-lg bg-aqar-500 px-6 py-3 font-semibold text-white transition-colors hover:bg-aqar-600"
        >
          View all properties
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-sand-200 bg-white py-8 text-center text-sm text-sand-400">
        <p>Aqar.ai: Master Thesis Project, Computer Science</p>
        <p className="mt-1">Tangier-Tetouan-Al Hoceima Region, Morocco</p>
      </footer>
    </div>
  );
}
