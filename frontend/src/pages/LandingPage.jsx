import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  Truck,
  MessageSquare,
  ArrowRight,
  CheckCircle2,
  BarChart3,
  Zap,
  Globe,
  TrendingDown,
  BadgeCheck,
  Bot,
  MapPin,
} from 'lucide-react';

const FeatureCard = ({ icon: Icon, title, description, gradient }) => (
  <div className="group relative bg-white rounded-2xl p-8 shadow-sm border border-slate-100 hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 hover:-translate-y-1">
    <div className={`inline-flex items-center justify-center w-14 h-14 rounded-xl ${gradient} mb-6 group-hover:scale-110 transition-transform duration-300`}>
      <Icon className="w-7 h-7 text-white" />
    </div>
    <h3 className="text-xl font-semibold text-slate-900 mb-3">{title}</h3>
    <p className="text-slate-600 leading-relaxed">{description}</p>
  </div>
);

const StatCard = ({ value, label, icon: Icon }) => (
  <div className="text-center">
    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm text-white mb-4">
      <Icon className="w-6 h-6" />
    </div>
    <div className="text-4xl font-bold text-white mb-2">{value}</div>
    <div className="text-emerald-100">{label}</div>
  </div>
);

const StepCard = ({ number, title, description }) => (
  <div className="relative flex gap-6">
    <div className="flex flex-col items-center">
      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-teal-700 to-emerald-600 text-white flex items-center justify-center font-bold text-lg shadow-lg shadow-emerald-200/70">
        {number}
      </div>
      {number < 4 && <div className="w-0.5 h-full bg-gradient-to-b from-teal-200 to-transparent mt-4" />}
    </div>
    <div className="pb-12">
      <h4 className="text-lg font-semibold text-slate-900 mb-2">{title}</h4>
      <p className="text-slate-600">{description}</p>
    </div>
  </div>
);

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-900 to-teal-700 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-slate-900">Risk<span className="text-teal-700">Guard</span></span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-slate-600 hover:text-slate-900 transition-colors">Features</a>
              <a href="#how-it-works" className="text-slate-600 hover:text-slate-900 transition-colors">How it Works</a>
            </div>
            <div className="flex items-center gap-3">
              <Link to="/login" className="px-4 py-2 text-slate-600 hover:text-slate-900 font-medium transition-colors">
                Login
              </Link>
              <Link to="/signup" className="px-5 py-2.5 bg-gradient-to-r from-teal-700 to-emerald-600 text-white rounded-lg hover:from-teal-800 hover:to-emerald-700 font-medium transition-all shadow-lg shadow-emerald-200/70 hover:shadow-xl hover:shadow-emerald-200">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-teal-50 text-teal-700 rounded-full text-sm font-medium mb-6">
                <Zap className="w-4 h-4" />
                AI-Powered COD Verification Platform
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-900 leading-tight mb-6">
                Stop Fake Orders
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-teal-700 to-emerald-600">
                  Before They Ship
                </span>
              </h1>
              <p className="text-xl text-slate-600 mb-8 leading-relaxed max-w-xl mx-auto lg:mx-0">
                Reduce RTO rates by up to 40% with AI-powered risk scoring and automated WhatsApp verification. Protect your business from fake COD orders.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-gradient-to-r from-teal-700 to-emerald-600 text-white rounded-xl font-semibold hover:from-teal-800 hover:to-emerald-700 transition-all shadow-lg shadow-teal-200/70 hover:shadow-xl hover:shadow-emerald-200 group"
                >
                  Get Started Now
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-white text-slate-700 rounded-xl font-semibold border border-slate-200 hover:bg-slate-50 transition-colors"
                >
                  See How It Works
                </a>
              </div>
              <div className="mt-10 flex items-center gap-8 justify-center lg:justify-start">
                <div className="flex -space-x-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 border-2 border-white flex items-center justify-center text-xs font-medium text-slate-600">
                      {String.fromCharCode(64 + i)}
                    </div>
                  ))}
                </div>
                <div className="text-left">
                  <div className="font-semibold text-slate-900">500+ Merchants</div>
                  <div className="text-sm text-slate-500">Trust RiskGuard</div>
                </div>
              </div>
            </div>

            <div className="relative animate-float">
              <div className="absolute inset-0 bg-gradient-to-br from-teal-400/20 to-emerald-400/20 rounded-3xl blur-3xl" />
              <div className="relative bg-white rounded-3xl shadow-2xl shadow-slate-200 border border-slate-100 p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-3 h-3 rounded-full bg-red-400" />
                  <div className="w-3 h-3 rounded-full bg-yellow-400" />
                  <div className="w-3 h-3 rounded-full bg-green-400" />
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-4 rounded-xl border border-green-100">
                      <div className="text-2xl font-bold text-green-600">80%</div>
                      <div className="text-sm text-green-700">RTO Reduction</div>
                    </div>
                    <div className="bg-gradient-to-br from-teal-50 to-emerald-50 p-4 rounded-xl border border-emerald-100">
                      <div className="text-2xl font-bold text-teal-700">95%</div>
                      <div className="text-sm text-emerald-700">Accuracy</div>
                    </div>
                    <div className="bg-gradient-to-br from-purple-50 to-fuchsia-50 p-4 rounded-xl border border-purple-100">
                      <div className="text-2xl font-bold text-purple-600">2.5x</div>
                      <div className="text-sm text-purple-700">ROI</div>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-slate-700">Order Verification</span>
                      <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">Live</span>
                    </div>
                    <div className="space-y-2">
                      {['Order received', 'Risk analysis complete', 'WhatsApp sent', 'Customer confirmed'].map((step, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <CheckCircle2 className="w-4 h-4 text-green-500" />
                          <span className="text-sm text-slate-600">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 bg-gradient-to-r from-slate-900 to-teal-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <StatCard value="70%" label="RTO Reduction" icon={TrendingDown} />
            <StatCard value="2K+" label="Orders Protected" icon={ShieldCheck} />
            <StatCard value="500+" label="Happy Merchants" icon={BadgeCheck} />
            <StatCard value="PKR 2M+" label="Money Saved" icon={BarChart3} />
          </div>
        </div>
      </section>

      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-1.5 bg-teal-50 text-teal-700 rounded-full text-sm font-medium mb-4">
              Powerful Features
            </span>
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-4">
              Everything You Need to Fight Fake Orders
            </h2>
            <p className="text-xl text-slate-600 max-w-3xl mx-auto">
              Our comprehensive platform combines AI, automation, and smart integrations to protect your business.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={ShieldCheck}
              title="AI Risk Scoring"
              description="Advanced machine learning analyzes customer history, address quality, and order patterns to detect fraud instantly."
              gradient="bg-gradient-to-br from-teal-600 to-emerald-600"
            />
            <FeatureCard
              icon={MessageSquare}
              title="WhatsApp Verification"
              description="Automated chatbots confirm order intent, verify addresses, and collect location pins through WhatsApp."
              gradient="bg-gradient-to-br from-green-500 to-emerald-600"
            />
            <FeatureCard
              icon={MapPin}
              title="Address Intelligence"
              description="Geocoding and area-level RTO history help validate addresses and identify high-risk delivery zones."
              gradient="bg-gradient-to-br from-orange-500 to-red-500"
            />
            <FeatureCard
              icon={Bot}
              title="Smart Chatbot Flows"
              description="Customizable conversation templates for order confirmation, address clarification, and high-risk challenges."
              gradient="bg-gradient-to-br from-teal-600 to-emerald-600"
            />
            <FeatureCard
              icon={Truck}
              title="RTO Prevention"
              description="Stop shipping to fake buyers before dispatch. Save on courier return charges and wasted inventory."
              gradient="bg-gradient-to-br from-cyan-600 to-emerald-500"
            />
            <FeatureCard
              icon={Globe}
              title="Multi-Platform Sync"
              description="Seamless integration with Shopify and custom platforms via REST API."
              gradient="bg-gradient-to-br from-slate-600 to-slate-700"
            />
          </div>
        </div>
      </section>

      <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8 bg-slate-50">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <span className="inline-block px-4 py-1.5 bg-teal-50 text-teal-700 rounded-full text-sm font-medium mb-4">
                Simple Process
              </span>
              <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-6">
                How RiskGuard Works
              </h2>
              <p className="text-lg text-slate-600 mb-10">
                Our intelligent system works silently in the background, analyzing every order and taking action automatically.
              </p>

              <div className="space-y-0">
                <StepCard
                  number={1}
                  title="Order Received"
                  description="New COD orders are automatically synced from your connected store in real-time."
                />
                <StepCard
                  number={2}
                  title="AI Risk Analysis"
                  description="Our ML engine analyzes customer history, address quality, and order patterns instantly."
                />
                <StepCard
                  number={3}
                  title="Smart Verification"
                  description="High-risk orders trigger automated WhatsApp messages to verify customer intent."
                />
                <StepCard
                  number={4}
                  title="Decision & Action"
                  description="Based on responses, orders are approved, flagged for review, or auto-cancelled."
                />
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-teal-400/10 to-emerald-400/10 rounded-3xl blur-2xl" />
              <div className="relative bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden">
                <div className="bg-gradient-to-r from-slate-900 to-teal-800 px-6 py-4">
                  <h4 className="text-white font-semibold">Live Order Analysis</h4>
                </div>
                <div className="p-6 space-y-4">
                  {[
                    { label: 'Customer Risk', value: 25, color: 'green' },
                    { label: 'Address Quality', value: 85, color: 'green' },
                    { label: 'Order Pattern', value: 60, color: 'yellow' },
                    { label: 'RTO Probability', value: 15, color: 'green' },
                  ].map((item, i) => (
                    <div key={i} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600">{item.label}</span>
                        <span className={`font-medium ${
                          item.color === 'green' ? 'text-green-600' :
                          item.color === 'yellow' ? 'text-yellow-600' : 'text-red-600'
                        }`}>{item.value}%</span>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            item.color === 'green' ? 'bg-green-500' :
                            item.color === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${item.value}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  <div className="pt-4 border-t border-slate-100">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-slate-900">Overall Score</span>
                      <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold">Low Risk</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-gradient-to-br from-slate-900 to-teal-800 rounded-3xl p-12 shadow-2xl shadow-emerald-200/70">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Ready to Eliminate Fake Orders?
            </h2>
            <p className="text-xl text-teal-100/90 mb-8 max-w-2xl mx-auto">
              Join 500+ merchants who have reduced their RTO rates and increased profitability with RiskGuard.
            </p>
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-teal-700 rounded-xl font-semibold hover:bg-teal-50 transition-colors shadow-lg group"
            >
              Get Started
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <p className="mt-4 text-teal-100/80 text-sm">No credit card required</p>
          </div>
        </div>
      </section>

      <footer className="bg-slate-900 text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 mb-12">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-slate-800 to-teal-600 flex items-center justify-center">
                  <ShieldCheck className="w-7 h-7 text-white" />
                </div>
                <div>
                  <span className="text-2xl font-bold text-white">Risk<span className="text-emerald-300">Guard</span></span>
                  <p className="text-sm mt-1">COD verification for merchants</p>
                </div>
              </div>
              <p className="text-slate-300 text-sm leading-relaxed">
                Reduce fake cash-on-delivery orders with risk scoring, store sync, and WhatsApp-based verification.
              </p>
            </div>

            <div>
              <h3 className="text-white font-semibold text-lg mb-6">Explore</h3>
              <div className="space-y-3 text-sm">
                <a href="#features" className="block hover:text-white transition-colors">Features</a>
                <a href="#how-it-works" className="block hover:text-white transition-colors">How It Works</a>
                <Link to="/login" className="block hover:text-white transition-colors">Merchant Login</Link>
                <Link to="/signup" className="block hover:text-white transition-colors">Create Account</Link>
              </div>
            </div>

            <div>
              <h3 className="text-white font-semibold text-lg mb-6">Support</h3>
              <div className="space-y-3 text-sm">
                <p>Need onboarding help or store setup support?</p>
                <a href="mailto:support@riskguard.pk" className="block hover:text-white transition-colors">
                  support@riskguard.pk
                </a>
                <p className="text-slate-500">
                  Product documentation, social channels, and public legal pages are not published yet.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4 text-sm">
            <div>
              <p>&copy; 2026 RiskGuard. All rights reserved.</p>
            </div>
            <div className="text-slate-500">
              Merchant dashboard and verification workflows are available after signup.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
