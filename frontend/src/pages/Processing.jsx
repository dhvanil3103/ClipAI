export default function Processing({ job }) {
  const skeletonCards = [
    { shimmerColor: 'rgba(202, 152, 255, 0.08)', delay: '0s', icon: 'movie', accent: 'primary' },
    { shimmerColor: 'rgba(255, 81, 250, 0.08)', delay: '0.5s', icon: 'trending_up', accent: 'secondary' },
    { shimmerColor: 'rgba(202, 152, 255, 0.08)', delay: '1s', icon: 'bolt', accent: 'primary' },
  ];

  return (
    <main className="pt-12 pb-12 px-6 md:px-12 min-h-screen relative overflow-hidden">
      {/* Ambient glows */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-secondary/10 rounded-full blur-[120px] pointer-events-none" />

      <section className="max-w-6xl mx-auto">
        {/* Processing Header */}
        <div className="flex flex-col items-center text-center mb-16 space-y-6 pt-12">
          <div className="relative w-24 h-24 flex items-center justify-center">
            <div className="absolute inset-0 border-4 border-primary/20 rounded-full" />
            <div className="absolute inset-0 border-4 border-transparent border-t-[#ca98ff] border-r-[#ff51fa] rounded-full animate-spin" />
            <span
              className="material-symbols-outlined text-4xl text-primary animate-pulse-soft"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              auto_awesome
            </span>
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl md:text-4xl font-headline font-bold tracking-tight text-on-surface">
              Curating Your Viral Moments
            </h1>
            <p className="text-on-surface-variant font-body text-lg animate-pulse-soft max-w-2xl mx-auto">
              AI is analyzing the transcript and extracting the most engaging moments...
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <span className="px-4 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] font-label uppercase tracking-widest text-tertiary-dim">
              Transcript Mapping
            </span>
            <span className="px-4 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] font-label uppercase tracking-widest text-on-surface-variant">
              Scene Detection
            </span>
            <span className="px-4 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/20 text-[10px] font-label uppercase tracking-widest text-on-surface-variant">
              Audio Cleanup
            </span>
          </div>
        </div>

        {/* Skeleton Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 md:gap-12 px-4 md:px-0">
          {skeletonCards.map((card, i) => (
            <div
              key={i}
              className="aspect-[9/16] relative rounded-3xl overflow-hidden bg-surface-container-low border border-outline-variant/10 shadow-[0_0_40px_-10px_rgba(0,0,0,0.5)]"
            >
              <div className="absolute inset-0 bg-gradient-to-tr from-surface-container-lowest via-surface-container-high to-surface-container-lowest" />
              {/* Shimmer */}
              <div
                className="absolute inset-0 w-full h-full -skew-x-12 animate-shimmer"
                style={{
                  background: `linear-gradient(90deg, transparent 0%, ${card.shimmerColor} 50%, transparent 100%)`,
                  animationDelay: card.delay,
                }}
              />
              {/* Placeholder elements */}
              <div className="absolute bottom-0 left-0 right-0 p-6 space-y-4">
                <div className="h-4 w-3/4 bg-surface-bright/40 rounded-full" />
                <div className="h-3 w-1/2 bg-surface-bright/20 rounded-full" />
                <div className="flex gap-2 pt-2">
                  <div
                    className={`h-8 w-20 border rounded-full backdrop-blur-md ${
                      card.accent === 'secondary'
                        ? 'bg-secondary/10 border-secondary/20'
                        : 'bg-primary/10 border-primary/20'
                    }`}
                  />
                  <div className="h-8 w-8 bg-surface-bright/40 rounded-full" />
                </div>
              </div>
              <div className="absolute top-6 right-6">
                <div className="w-12 h-12 rounded-2xl bg-surface-bright/30 backdrop-blur-xl flex items-center justify-center">
                  <span className="material-symbols-outlined text-on-surface/30">{card.icon}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer Task Status */}
        <div className="mt-20 glass-panel p-6 rounded-3xl border border-outline-variant/10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-full bg-surface-container-lowest flex items-center justify-center border border-outline-variant/20 shrink-0">
              <span className="material-symbols-outlined text-primary text-xl">description</span>
            </div>
            <div>
              <p className="font-label text-xs uppercase tracking-widest text-on-surface-variant">
                Currently Processing
              </p>
              <p className="font-headline font-semibold truncate max-w-[240px]">
                {job?.url || 'Processing...'}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-label text-[10px] uppercase tracking-widest text-on-surface-variant">
              Estimated Time
            </p>
            <p className="font-headline font-bold text-xl text-primary">
              ~ 2:00{' '}
              <span className="text-sm font-normal text-on-surface-variant">remaining</span>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
