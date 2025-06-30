import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind()],
  output: 'static',
  // Vercelでの本番デプロイ用設定
  site: 'https://ai-info-aggregator.vercel.app',
  // base: '/ai-info-aggregator', // Vercelでは不要
});