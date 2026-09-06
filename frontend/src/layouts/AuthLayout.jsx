import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { ShieldCheck, MessageSquare, BarChart3, Zap } from 'lucide-react';

const FeatureItem = ({ icon: Icon, title, description }) => (
  <div className="flex items-start gap-4">
    <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
      <Icon className="w-5 h-5 text-teal-100" />
    </div>
    <div>
      <h4 className="font-medium text-white">{title}</h4>
      <p className="text-sm text-teal-100/90 mt-0.5">{description}</p>
    </div>
  </div>
);

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-slate-900 via-teal-900 to-emerald-800 p-12 flex-col justify-between relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 left-0 w-96 h-96 bg-white rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
          <div className="absolute bottom-0 right-0 w-96 h-96 bg-white rounded-full blur-3xl translate-x-1/2 translate-y-1/2" />
        </div>
        
        <div className="relative z-10">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <ShieldCheck className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-bold text-white">RiskGuard</span>
          </Link>
        </div>
        
        <div className="relative z-10 space-y-8">
          <div>
            <h2 className="text-3xl font-bold text-white mb-4">
              Protect Your Business from Fake COD Orders
            </h2>
            <p className="text-lg text-teal-100/90">
              Join 500+ merchants who have reduced their RTO rates by up to 40% with our AI-powered verification platform.
            </p>
          </div>
          
          <div className="space-y-6">
            <FeatureItem 
              icon={Zap}
              title="AI-Powered Risk Analysis"
              description="Instant fraud detection on every order"
            />
            <FeatureItem 
              icon={MessageSquare}
              title="WhatsApp Verification"
              description="Automated customer confirmation flows"
            />
            <FeatureItem 
              icon={BarChart3}
              title="Real-time Analytics"
              description="Track RTO trends and savings"
            />
          </div>
        </div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-4">
            <div className="flex -space-x-2">
              {['A', 'B', 'C', 'D'].map((letter, i) => (
                <div key={i} className="w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm border-2 border-white/30 flex items-center justify-center text-xs font-medium text-white">
                  {letter}
                </div>
              ))}
            </div>
            <p className="text-teal-100/90 text-sm">
              <span className="font-semibold text-white">500+</span> merchants trust RiskGuard
            </p>
          </div>
        </div>
      </div>

      {/* Right Side - Auth Form */}
      <div className="w-full lg:w-1/2 flex flex-col min-h-screen bg-slate-50">
        {/* Mobile Header */}
        <div className="lg:hidden p-6 bg-gradient-to-r from-slate-900 to-teal-800">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-white">RiskGuard</span>
          </Link>
        </div>

        {/* Form Container */}
        <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
          <div className="w-full max-w-md">
            <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-100 p-8 sm:p-10">
              <Outlet />
            </div>
            
            <p className="text-center text-sm text-slate-500 mt-8">
              By continuing, you agree to our{' '}
              <a href="#" className="text-teal-700 hover:underline">Terms of Service</a>
              {' '}and{' '}
              <a href="#" className="text-teal-700 hover:underline">Privacy Policy</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
