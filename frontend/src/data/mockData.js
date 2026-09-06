export const mockStats = {
  rtoPercentage: 12.5,
  fraudScore: 8.2,
  savings: 15420,
  totalOrders: 1250,
  pendingVerification: 45,
  codOrdersToday: 24
};

export const mockOrders = [
  {
    id: "ORD-001",
    customer: "Ali Khan",
    phone: "+92 300 1234567",
    amount: 4500,
    status: "Pending",
    riskScore: 85,
    riskLevel: "High",
    date: "2023-10-25",
    city: "Karachi",
    items: ["Wireless Earbuds", "Smart Watch"],
    chatStatus: "Unverified",
    addressScore: 85,
    fraudScore: 15,
    rtoProbability: "Low",
    recommendedAction: "Verify Address"
  },
  {
    id: "ORD-002",
    customer: "Sara Ahmed",
    phone: "+92 321 9876543",
    amount: 1200,
    status: "Verified",
    riskScore: 15,
    riskLevel: "Low",
    date: "2023-10-25",
    city: "Lahore",
    items: ["Cotton T-Shirt"],
    chatStatus: "Confirmed",
    addressScore: 98,
    fraudScore: 5,
    rtoProbability: "Very Low",
    recommendedAction: "Ship Order"
  },
  {
    id: "ORD-003",
    customer: "Bilal T.",
    phone: "+92 333 5555555",
    amount: 8900,
    status: "Rejected",
    riskScore: 92,
    riskLevel: "Critical",
    date: "2023-10-24",
    city: "Islamabad",
    items: ["Gaming Keyboard", "Mouse"],
    chatStatus: "Denied",
    addressScore: 45,
    fraudScore: 88,
    rtoProbability: "High",
    recommendedAction: "Cancel Order"
  },
  {
    id: "ORD-004",
    customer: "Zainab B.",
    phone: "+92 345 1112223",
    amount: 3200,
    status: "Pending",
    riskScore: 45,
    riskLevel: "Medium",
    date: "2023-10-24",
    city: "Faisalabad",
    items: ["Makeup Kit"],
    chatStatus: "No Response",
    addressScore: 60,
    fraudScore: 45,
    rtoProbability: "Medium",
    recommendedAction: "Call Customer"
  },
  {
    id: "ORD-005",
    customer: "Usman G.",
    phone: "+92 312 4443332",
    amount: 15000,
    status: "Verified",
    riskScore: 10,
    riskLevel: "Low",
    date: "2023-10-23",
    city: "Multan",
    items: ["Smartphone"],
    chatStatus: "Confirmed",
    addressScore: 92,
    fraudScore: 8,
    rtoProbability: "Low",
    recommendedAction: "Ship Order"
  }
];

export const mockOrderDetail = {
  id: "ORD-001",
  customer: {
    name: "Ali Khan",
    phone: "+92 300 1234567",
    email: "ali.khan@example.com",
    address: "House 123, Street 4, Block 5, Gulshan-e-Iqbal, Karachi",
    city: "Karachi",
    history: {
      totalOrders: 5,
      delivered: 2,
      rto: 3,
      rtoRate: "60%"
    }
  },
  order: {
    amount: 4500,
    date: "2023-10-25 14:30",
    items: [
      { name: "Wireless Earbuds", price: 2000, qty: 1 },
      { name: "Smart Watch", price: 2500, qty: 1 }
    ],
    paymentMethod: "COD"
  },
  riskAnalysis: {
    totalScore: 85,
    factors: [
      { name: "High RTO History", score: 90, level: "Critical" },
      { name: "Address Mismatch", score: 60, level: "Medium" },
      { name: "High Value Order", score: 40, level: "Low" }
    ],
    recommendation: "Verify"
  },
  addressVerification: {
    enteredAddress: "House 123, Street 4, Block 5, Gulshan-e-Iqbal, Karachi",
    suggestedAddress: "House 123, Street 4, Block 5, Gulshan-e-Iqbal, Karachi City, Sindh, Pakistan",
    confidenceScore: 95,
    status: "Valid",
    mapPreviewUrl: "https://via.placeholder.com/600x300" 
  },
  whatsappInteraction: {
    lastMessageSent: "2023-10-25 14:35",
    customerResponse: "Yes, confirm order",
    timeToFirstReply: "5 mins",
    addressClarification: "N/A",
    nudgesSent: 0
  },
  chatLog: [
    { sender: "Bot", message: "Hi Ali, please confirm your order for Wireless Earbuds...", time: "14:31" },
    { sender: "User", message: "Yes", time: "14:35" },
    { sender: "Bot", message: "Please share your location pin.", time: "14:35" },
    { sender: "User", message: "(No response)", time: "-" }
  ]
};
