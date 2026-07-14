import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/products/**",
      },
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/ex/**",
      },
      {
        protocol: "https",
        hostname: "www.pokemon-card.com",
        pathname: "/assets/images/card_images/**",
      },
      {
        protocol: "https",
        hostname: "cdn.collectory.cc",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "data1.pokemonkorea.co.kr",
        pathname: "/**",
      },
      {
        protocol: "https",
        hostname: "card.yuyu-tei.jp",
        pathname: "/poc/**",
      },
    ],
  },
};

export default nextConfig;
