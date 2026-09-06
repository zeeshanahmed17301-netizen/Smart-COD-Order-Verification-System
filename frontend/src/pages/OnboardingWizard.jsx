import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Store, Settings, CheckCircle, ArrowRight, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import accountsApi from '../api/accounts';
import { useAuth } from '../contexts/AuthContext';
import { getErrorMessage } from '../api/client';

const steps = [
  { id: 1, title: 'Business Setup', icon: Store },
  { id: 2, title: 'Preferences', icon: Settings },
];

const SUCCESS_STEP = steps.length + 1; // 3

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const location = useLocation();
  const { refreshProfile } = useAuth();
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    storeName: location.state?.storeName || '',
    category: '',
    country: 'Pakistan',
    autoSend: 'immediately',
    autoCancel: 'off',
    language: 'urdu'
  });

  // Step 1 must be filled before onboarding can be saved.
  const isBusinessStepValid = formData.storeName.trim() !== '' && formData.category !== '';
  const canProceed = currentStep !== 1 || isBusinessStepValid;

  const handleNext = async () => {
    if (currentStep === steps.length) {
      // Last data step — persist onboarding and show the success screen.
      setIsLoading(true);
      setError('');
      try {
        await accountsApi.saveOnboarding({
          store_name: formData.storeName,
          category: formData.category,
          country: formData.country,
          auto_send: formData.autoSend,
          auto_cancel: formData.autoCancel,
          language: formData.language,
        });
        await refreshProfile();
        setCurrentStep(SUCCESS_STEP);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setIsLoading(false);
      }
    } else if (currentStep === SUCCESS_STEP) {
      navigate('/dashboard', { replace: true });
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1 && currentStep !== SUCCESS_STEP) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const nextLabel = currentStep === SUCCESS_STEP
    ? 'Go to Dashboard'
    : currentStep === steps.length
      ? 'Finish Setup'
      : 'Next';

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl overflow-hidden">
        {/* Progress Bar */}
        <div className="bg-slate-50 border-b border-slate-200 p-6">
          <div className="flex items-center justify-between relative">
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-slate-200 -z-10" />
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-teal-700 -z-10 transition-all duration-500"
              style={{ width: `${Math.min(100, ((currentStep - 1) / (steps.length - 1)) * 100)}%` }}
            />
            {steps.map((step) => {
              const Icon = step.icon;
              const isActive = step.id === currentStep;
              const isCompleted = step.id < currentStep;

              return (
                <div key={step.id} className="flex flex-col items-center gap-2 bg-slate-50 px-2">
                  <div className={clsx(
                    "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300",
                    isActive ? "bg-teal-700 text-white shadow-lg shadow-emerald-200/70 scale-110" :
                    isCompleted ? "bg-green-500 text-white" :
                    "bg-white border-2 border-slate-200 text-slate-400"
                  )}>
                    {isCompleted ? <CheckCircle className="w-6 h-6" /> : <Icon className="w-5 h-5" />}
                  </div>
                  <span className={clsx(
                    "text-xs font-medium transition-colors duration-300",
                    isActive ? "text-teal-700" :
                    isCompleted ? "text-green-600" :
                    "text-slate-400"
                  )}>
                    {step.title}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="p-8 min-h-[400px]">
          {error && (
            <div className="flex items-center gap-3 p-4 mb-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <p className="text-sm">{error}</p>
            </div>
          )}
          {currentStep === 1 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <h2 className="text-2xl font-bold text-slate-900">Tell us about your business</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Store Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="storeName"
                    value={formData.storeName}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-transparent"
                    placeholder="e.g. My Awesome Store"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Business Category <span className="text-red-500">*</span>
                  </label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-transparent"
                  >
                    <option value="">Select a category</option>
                    <option value="fashion">Fashion & Apparel</option>
                    <option value="electronics">Electronics</option>
                    <option value="beauty">Beauty & Health</option>
                    <option value="home">Home & Living</option>
                    <option value="grocery">Grocery</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
                  <input
                    name="country"
                    value={formData.country}
                    disabled
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-500"
                  />
                </div>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <h2 className="text-2xl font-bold text-slate-900">Verification Preferences</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Auto-send WhatsApp confirmation</label>
                  <select
                    name="autoSend"
                    value={formData.autoSend}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-transparent"
                  >
                    <option value="immediately">Immediately</option>
                    <option value="1min">After 1 min</option>
                    <option value="5min">After 5 min</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Auto-cancel unconfirmed orders after</label>
                  <select
                    name="autoCancel"
                    value={formData.autoCancel}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-transparent"
                  >
                    <option value="off">Off</option>
                    <option value="30min">30 min</option>
                    <option value="1hour">1 hour</option>
                    <option value="2hours">2 hours</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Default Language</label>
                  <select
                    name="language"
                    value={formData.language}
                    onChange={handleChange}
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-600 focus:border-transparent"
                  >
                    <option value="urdu">Urdu</option>
                    <option value="english">English</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {currentStep === SUCCESS_STEP && (
            <div className="text-center space-y-6 animate-in fade-in zoom-in duration-500 py-10">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-slate-900">You&apos;re all set!</h2>
                <p className="text-slate-500 mt-2 max-w-md mx-auto">
                  Your preferences are saved. Next, connect your store from the dashboard to start
                  importing and verifying orders.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 border-t border-slate-200 p-6 flex justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 1 || currentStep === SUCCESS_STEP}
            className="px-6 py-2.5 rounded-xl text-slate-600 font-medium hover:bg-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            onClick={handleNext}
            disabled={isLoading || !canProceed}
            className="px-6 py-2.5 bg-teal-700 text-white rounded-xl font-medium hover:bg-teal-800 transition-colors shadow-lg shadow-emerald-200/70 flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</>
            ) : (
              <>{nextLabel}
              {currentStep !== SUCCESS_STEP && <ArrowRight className="w-4 h-4" />}</>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
