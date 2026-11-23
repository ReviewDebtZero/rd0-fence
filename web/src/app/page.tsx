import { Footer } from "@/components/Footer";
import { Nav } from "@/components/Nav";
import { Benchmark, Demo, Hero, HowItWorks, Install, Limits, Problem, Research } from "@/components/Sections";
import { Reveal } from "@/components/motion/Reveal";

export default function Page() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        {[Problem, Demo, Benchmark, HowItWorks, Install, Limits, Research].map((S) => (
          <Reveal key={S.name}>
            <S />
          </Reveal>
        ))}
      </main>
      <Footer />
    </>
  );
}
