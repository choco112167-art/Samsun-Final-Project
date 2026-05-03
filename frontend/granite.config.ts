import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'samsun-newsapp',
  brand: {
    displayName: '삼선뉴스',
    primaryColor: '#3182F6',
    icon: '/favicon.svg',
  },
  web: {
    // 실기기 토스앱 테스트 시 AIT_WEB_HOST=PC내부IP 로 실행한다.
    // 예: Windows PowerShell `$env:AIT_WEB_HOST="192.168.45.27"; npm run ait:dev`
    host: process.env.AIT_WEB_HOST ?? 'localhost',
    port: 5173,
    commands: {
      dev: 'vite --host 0.0.0.0 --port 5173',
      build: 'vite build',
    },
  },
  permissions: [],
  outdir: 'dist',
});
