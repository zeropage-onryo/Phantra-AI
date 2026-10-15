import Link from "next/link";
import "@/components/landing/vesper.css";
import { VesperStage } from "@/components/landing/vesper-stage";
import {
  Flicker,
  MakeLikeLink,
  ModelsDrift,
  PrefillButton,
  Rise,
  ShowcaseTile,
} from "@/components/landing/vesper-motion";
import { SHOWCASE, VESPER_ALT, reelClip, vesperSrc } from "@/components/landing/vesper-content";

// The homepage below the hero (2026-10-15, the Vesper mockup Mike approved,
// replacing the pipeline, features, frames, work, starting-points and CTA
// sections): the lantern stage with Vesper's pitch and the playable demo,
// the five starting points, the showcase of real clips, the models strip and
// the closing CTA. Every heading and line of copy here is a server component,
// so it is in the HTML a crawler and a JS-off visitor read; only the demo,
// the clip tiles and the motion are client leaves (vesper-stage.tsx,
// vesper-motion.tsx). Copy is the mockup's, word for word, with the pitch
// as Mike edited it.

/* eslint-disable @next/next/no-img-element -- the mascot set on R2, sized by CSS */

const TRY = "/studio";

export function VesperSection() {
  return (
    <section className="vh-scope vh-lsec" id="vesper" aria-labelledby="vesper-h">
      <span id="how" className="vh-anchor" aria-hidden />
      <div className="vh-wrap">
        <div className="vh-pitch">
          <h2 className="serif" id="vesper-h">
            Meet Vesper, your Personal AI Agent.
          </h2>
          <p className="vh-sub">
            Vesper works alongside you on every project. Tell it what you&rsquo;re making and it plans the shots,
            writes the scene, and generates images and video.
          </p>
          <div className="vh-pitch-acts">
            <Link className="vh-btn vh-btn-white" href={TRY}>
              Try Vesper free
            </Link>
            <a className="vh-btn vh-btn-quiet" href="#stage">
              See Vesper work ↓
            </a>
          </div>
        </div>
      </div>

      <Rise className="vh-rise-top">
        <VesperStage
          captions={
            <ul className="vh-caps">
              <li>
                <span className="vh-k">01</span>Remembers your project: the brief, the look and what you liked.
              </li>
              <li>
                <span className="vh-k">02</span>Picks the model for each shot. You can always change it.
              </li>
              <li>
                <span className="vh-k">03</span>Asks before it spends a credit.
              </li>
            </ul>
          }
        />
      </Rise>

      <div className="vh-wrap">
        <div className="vh-below">
          <p>Vesper suggests the model for each shot. You can always pick another.</p>
          <Link className="vh-btn vh-btn-white" href={TRY}>
            Try Vesper free
          </Link>
        </div>
      </div>
    </section>
  );
}

const ICON = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

const STARTS: { title: string; body: string; example: string; icon: React.ReactNode }[] = [
  {
    title: "An idea",
    body: "A sentence is enough. Vesper plans the rest.",
    example: "A 15-second teaser: a paper boat sails down a rainy street at night.",
    icon: (
      <>
        <path d="M9 18h6M10 21h4" />
        <path d="M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z" />
      </>
    ),
  },
  {
    title: "A script",
    body: "Paste a scene and get it as timed shots.",
    example: "INT. DINER – NIGHT. A waitress slides a coffee across the counter. The door opens; the bell rings.",
    icon: (
      <>
        <path d="M6 3h9l4 4v14H6z" />
        <path d="M15 3v4h4M9 11h7M9 14h7M9 17h4" />
      </>
    ),
  },
  {
    title: "A product page",
    body: "Drop a link. Vesper reads the product and pictures it.",
    example: "Make a 9:16 ad from my product page: https://example.com/products/trail-runner",
    icon: (
      <>
        <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
        <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
      </>
    ),
  },
  {
    title: "An image",
    body: "Bring a still and turn it into motion.",
    example: "Turn my still into motion: slow push in, steam rising from the cup.",
    icon: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <circle cx="9" cy="9.5" r="1.6" />
        <path d="M21 16l-5-5-9 9" />
      </>
    ),
  },
  {
    title: "A clip",
    body: "Upscale it, reframe it, or give it sound.",
    example: "Reframe my clip to 9:16 and give it rain and distant thunder.",
    icon: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="M3 9h18M3 15h18M7.5 5v4M12 5v4M16.5 5v4M7.5 15v4M12 15v4M16.5 15v4" />
      </>
    ),
  },
];

export function StartAnywhereSection() {
  return (
    <section className="vh-scope vh-blk" id="starts" aria-labelledby="starts-h">
      <span id="work" className="vh-anchor" aria-hidden />
      <Rise className="vh-wrap">
        <div className="vh-blk-h">
          <span className="vh-eyebrow">
            <i />
            Start anywhere
          </span>
          <h2 className="serif" id="starts-h">
            Start with whatever you&rsquo;ve got.
          </h2>
        </div>
        <div className="vh-starts">
          <div className="vh-st-scroll" role="region" aria-label="Starting points" tabIndex={0}>
            <ul className="vh-st-row">
              {STARTS.map((s) => (
                <li key={s.title}>
                  <PrefillButton text={s.example} className="vh-sp">
                    <svg viewBox="0 0 24 24" aria-hidden {...ICON}>
                      {s.icon}
                    </svg>
                    <b>{s.title}</b>
                    <span>{s.body}</span>
                    <i>Start here</i>
                  </PrefillButton>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Rise>
    </section>
  );
}

export function ShowcaseSection() {
  return (
    <section className="vh-scope vh-blk" id="showcase" aria-labelledby="show-h">
      <span id="frames" className="vh-anchor" aria-hidden />
      <Rise className="vh-wrap">
        <div className="vh-blk-h">
          <span className="vh-eyebrow">
            <i />
            Made in Phantra
          </span>
          <h2 className="serif" id="show-h">
            Made in Phantra.
          </h2>
        </div>
        <div className="vh-show">
          {SHOWCASE.map((tile) => {
            const clip = reelClip(tile.name);
            return (
              <ShowcaseTile
                key={tile.name}
                mp4={clip.mp4}
                poster={clip.poster}
                model={clip.model}
                caption={tile.line ?? clip.title}
                ar={tile.ar}
              />
            );
          })}
        </div>
        <div className="vh-show-foot">
          <MakeLikeLink className="vh-qlink">Make one like these →</MakeLikeLink>
        </div>
      </Rise>
    </section>
  );
}

export function ModelsStripSection() {
  return (
    <section className="vh-scope vh-blk" id="models" aria-labelledby="models-h">
      <Rise>
        <div className="vh-wrap">
          <div className="vh-blk-h">
            <span className="vh-eyebrow">
              <i />
              Every top model
            </span>
            <h2 className="serif" id="models-h">
              Every top model, one place.
            </h2>
            <p>Vesper picks the model for each shot. You can always choose another.</p>
          </div>
        </div>
        <ModelsDrift />
        <div className="vh-wrap vh-mq-foot">
          <Link className="vh-qlink" href="/models">
            See all models →
          </Link>
        </div>
      </Rise>
    </section>
  );
}

export function ClosingCtaSection() {
  return (
    <section className="vh-scope vh-cta" aria-labelledby="cta-h">
      <Rise className="vh-wrap vh-cta-in">
        <div className="vh-cta-v">
          <span className="vh-lamp" aria-hidden>
            <Flicker className="vh-glow" />
          </span>
          <img
            src={vesperSrc("made", 640)}
            alt={`${VESPER_ALT}, with the lantern lit green`}
            width={150}
            height={150}
            loading="lazy"
            decoding="async"
          />
        </div>
        <div className="vh-cta-tx">
          <h2 className="serif" id="cta-h">
            Say it. See it. Ship it.
          </h2>
          <div className="vh-cta-acts">
            <Link className="vh-btn vh-btn-white" href={TRY}>
              Try Vesper free
            </Link>
            <Link className="vh-btn vh-btn-quiet" href="/pricing">
              See pricing
            </Link>
          </div>
        </div>
      </Rise>
    </section>
  );
}
