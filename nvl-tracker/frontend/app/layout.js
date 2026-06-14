export const metadata = {
  title: "NVL Price Tracker — Bảng giá Nguyên Vật Liệu",
  description: "Theo dõi & phân tích biến động giá nguyên vật liệu tự động",
};

export default function RootLayout({ children }) {
  return (
    <html lang="vi">
      <body
        style={{
          margin: 0,
          fontFamily:
            "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          background: "#0f172a",
          color: "#e2e8f0",
        }}
      >
        {children}
      </body>
    </html>
  );
}
