export const SafeAreaProvider = ({ children }: any) => children;
export const useSafeAreaInsets = () => ({ top: 0, bottom: 0, left: 0, right: 0 });
export const SafeAreaInsetsContext = {
  Consumer: ({ children }: any) => children({}),
};
export const SafeAreaView = ({ children }: any) => children;
