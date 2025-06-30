import { defineConfig } from 'astro/config';

export default defineConfig({
  integrations: [],
  output: 'static',
  // Vercelでの本番デプロイ用設定
  site: 'https://ai-info-aggregator.vercel.app',
  // base: '/ai-info-aggregator', // Vercelでは不要
});