import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Bot,
  CheckCircle,
  Clock,
  Globe,
  MessageSquare,
  Save,
  Smartphone,
} from 'lucide-react';
import clsx from 'clsx';
import chatbotApi from '../api/chatbot';
import { getErrorMessage } from '../api/client';

const delayOptions = [
  { value: 0, label: 'Instant' },
  { value: 1, label: '1 minute' },
  { value: 5, label: '5 minutes' },
  { value: 15, label: '15 minutes' },
];

const timeoutOptions = [
  { value: 0, label: 'Disabled' },
  { value: 60, label: '1 hour' },
  { value: 720, label: '12 hours' },
  { value: 1440, label: '24 hours' },
  { value: 2880, label: '48 hours' },
];

export default function ChatbotSettingsPage() {
  const [activeTab, setActiveTab] = useState('general');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formData, setFormData] = useState({
    is_connected: false,
    platform_is_configured: false,
    platform_whatsapp_number: '',
    auto_send_confirmation: true,
    confirmation_delay_minutes: 0,
    auto_cancel_timeout_minutes: 0,
    language: 'urdu',
    greeting_template: '',
    confirmation_template: '',
  });

  useEffect(() => {
    const loadSettings = async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await chatbotApi.getSettings();
        setFormData({
          is_connected: Boolean(data.is_connected),
          platform_is_configured: Boolean(data.platform_is_configured),
          platform_whatsapp_number: data.platform_whatsapp_number || '',
          auto_send_confirmation: Boolean(data.auto_send_confirmation),
          confirmation_delay_minutes: data.confirmation_delay_minutes ?? 0,
          auto_cancel_timeout_minutes: data.auto_cancel_timeout_minutes ?? 0,
          language: data.language || 'urdu',
          greeting_template: data.greeting_template || '📦 *Order Summary*\n\n📦 Items: {items}\n💰 Total: {amount}\n👤 Name: {customer_name}\n📍 Address: {current_address}\n🗒️ Order: #{order_id}\n\n🚀 We will ship once you confirm!\n\nReply with:\n✅ *1* - Confirm Order\n📞 *2* - Cancel',
          confirmation_template: data.confirmation_template || '',
        });
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    if (error) setError('');
    if (success) setSuccess('');
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        auto_send_confirmation: formData.auto_send_confirmation,
        language: formData.language,
        greeting_template: formData.greeting_template,
        confirmation_template: formData.confirmation_template,
        confirmation_delay_minutes: Number(formData.confirmation_delay_minutes),
        auto_cancel_timeout_minutes: Number(formData.auto_cancel_timeout_minutes),
      };

      const { data } = await chatbotApi.updateSettings(payload);
      setFormData((prev) => ({
        ...prev,
        is_connected: Boolean(data.is_connected),
        platform_is_configured: Boolean(data.platform_is_configured),
        platform_whatsapp_number: data.platform_whatsapp_number || '',
      }));
      setSuccess('Chatbot settings saved.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Chatbot Settings</h1>
          <p className="mt-2 text-slate-500">
            Configure the WhatsApp verification flow, templates, and automation rules.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || loading}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-teal-700 to-emerald-600 px-6 py-3 font-semibold text-white disabled:opacity-60"
        >
          <Save className="h-5 w-5" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      <div className="flex w-fit gap-2 rounded-xl bg-slate-100 p-1.5">
        {[
          ['general', 'General'],
          ['templates', 'Templates'],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setActiveTab(value)}
            className={clsx(
              'rounded-lg px-5 py-2.5 text-sm font-medium transition-all',
              activeTab === value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {(error || success) && (
        <div className="space-y-3">
          {error && (
            <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              <CheckCircle className="h-4 w-4" />
              <span>{success}</span>
            </div>
          )}
        </div>
      )}

      <div className="grid gap-8 xl:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          {activeTab === 'general' && (
            <>
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <Bot className="h-5 w-5 text-slate-400" />
                  Platform WhatsApp
                </h2>
                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sender number</p>
                    <p className="mt-1 text-sm font-semibold text-slate-900">
                      {formData.platform_whatsapp_number || 'Not configured'}
                    </p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Provider status</p>
                    <p className={clsx('mt-1 text-sm font-semibold', formData.platform_is_configured ? 'text-emerald-700' : 'text-red-700')}>
                      {formData.platform_is_configured ? 'Configured' : 'Missing platform credentials'}
                    </p>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <Clock className="h-5 w-5 text-slate-400" />
                  Automation
                </h2>
                <div className="mt-6 space-y-4">
                  <label className="flex items-center justify-between rounded-xl border border-slate-200 p-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">Auto-send confirmation</p>
                      <p className="text-sm text-slate-500">Start the verification flow automatically after order creation.</p>
                    </div>
                    <input
                      name="auto_send_confirmation"
                      type="checkbox"
                      checked={formData.auto_send_confirmation}
                      onChange={handleChange}
                      className="h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-600"
                    />
                  </label>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <label className="mb-2 block text-sm font-medium text-slate-700">Confirmation delay</label>
                      <select
                        name="confirmation_delay_minutes"
                        value={formData.confirmation_delay_minutes}
                        onChange={handleChange}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                      >
                        {delayOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="mb-2 block text-sm font-medium text-slate-700">Timeout window</label>
                      <select
                        name="auto_cancel_timeout_minutes"
                        value={formData.auto_cancel_timeout_minutes}
                        onChange={handleChange}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                      >
                        {timeoutOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="mb-2 block text-sm font-medium text-slate-700">Language</label>
                    <select
                      name="language"
                      value={formData.language}
                      onChange={handleChange}
                      className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                    >
                      <option value="urdu">Urdu</option>
                      <option value="english">English</option>
                      <option value="mixed">Mixed</option>
                    </select>
                  </div>
                </div>
              </section>
            </>
          )}

          {activeTab === 'templates' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                <MessageSquare className="h-5 w-5 text-slate-400" />
                Message Templates
              </h2>
              <div className="mt-6 space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Greeting template</label>
                  <textarea
                    name="greeting_template"
                    rows="5"
                    value={formData.greeting_template}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Confirmation template</label>
                  <textarea
                    name="confirmation_template"
                    rows="5"
                    value={formData.confirmation_template}
                    onChange={handleChange}
                    className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                  />
                </div>
              </div>
            </section>
          )}

        </div>

        <aside className="space-y-6">
          <section className="rounded-2xl bg-gradient-to-br from-slate-900 to-teal-800 p-6 text-white shadow-sm">
            <h3 className="text-lg font-semibold">Connection Status</h3>
            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-emerald-100">WhatsApp</span>
                <span className={clsx('font-semibold', formData.is_connected ? 'text-white' : 'text-amber-200')}>
                  {formData.is_connected ? 'Platform connected' : 'Not configured'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-emerald-100">Language</span>
                <span className="font-semibold capitalize text-white">{formData.language}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-emerald-100">Auto-send</span>
                <span className="font-semibold text-white">{formData.auto_send_confirmation ? 'Enabled' : 'Disabled'}</span>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Applied Settings</h3>
            <div className="mt-4 space-y-4 text-sm text-slate-600">
              <div className="flex items-center gap-3">
                <Smartphone className="h-4 w-4 text-slate-400" />
                <span>{formData.platform_whatsapp_number || 'No platform sender configured'}</span>
              </div>
              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-slate-400" />
                <span>Confirmation delay: {Number(formData.confirmation_delay_minutes)} minute(s)</span>
              </div>
              <div className="flex items-center gap-3">
                <Globe className="h-4 w-4 text-slate-400" />
                <span>Timeout: {Number(formData.auto_cancel_timeout_minutes)} minute(s)</span>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
