import { defineConfig } from '@apps-in-toss/web-framework/config';

export default defineConfig({
  appName: 'samsun-newsapp',
  brand: {
    displayName: 'samsun-newsapp', // 화면에 노출될 앱의 한글 이름으로 바꿔주세요.
    primaryColor: '#3182F6', // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
    icon: 'file:///C:/Users/Min/Downloads/samsun_logo_light.png', // 화면에 노출될 앱의 아이콘 이미지 주소로 바꿔주세요.
  },
  web: {
    host: '', //host는 ipconfig에 나오는 IPv4 주소를 입력해주세요
    port: 5173,   
    commands: {
      dev: 'vite --host',
      build: 'tsc -b && vite build',
    },
  },
  permissions: [],
  outdir: 'dist',
});
