import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "./ProtectedRoute";

const LoginPage = lazy(() => import("@/features/auth/LoginPage").then(m => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import("@/features/auth/RegisterPage").then(m => ({ default: m.RegisterPage })));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage").then(m => ({ default: m.DashboardPage })));
const IdentifiersPage = lazy(() => import("@/features/identifiers/IdentifiersPage").then(m => ({ default: m.IdentifiersPage })));
const ScansPage = lazy(() => import("@/features/scans/ScansPage").then(m => ({ default: m.ScansPage })));
const ScanDetailPage = lazy(() => import("@/features/scans/ScanDetailPage").then(m => ({ default: m.ScanDetailPage })));
const FindingsPage = lazy(() => import("@/features/findings/FindingsPage").then(m => ({ default: m.FindingsPage })));
const ScoresPage = lazy(() => import("@/features/scores/ScoresPage").then(m => ({ default: m.ScoresPage })));
const RecommendationsPage = lazy(() => import("@/features/recommendations/RecommendationsPage").then(m => ({ default: m.RecommendationsPage })));
const IdentityPage = lazy(() => import("@/features/identity/IdentityPage").then(m => ({ default: m.IdentityPage })));
const RemediationPage = lazy(() => import("@/features/remediation/RemediationPage").then(m => ({ default: m.RemediationPage })));
const PrivacyPage = lazy(() => import("@/features/privacy/PrivacyPage").then(m => ({ default: m.PrivacyPage })));
const OnboardingPage = lazy(() => import("@/features/onboarding/OnboardingPage").then(m => ({ default: m.OnboardingPage })));
const TimelinePage = lazy(() => import("@/features/temporal/TimelinePage").then(m => ({ default: m.TimelinePage })));
const ReviewQueuePage = lazy(() => import("@/features/temporal/ReviewQueuePage").then(m => ({ default: m.ReviewQueuePage })));

const Suspended = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={
    <div className="flex h-[50vh] w-full items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  }>
    {children}
  </Suspense>
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/app/onboarding" replace />,
  },
  {
    path: "/login",
    element: <Suspended><LoginPage /></Suspended>,
  },
  {
    path: "/register",
    element: <Suspended><RegisterPage /></Suspended>,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/app",
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <Suspended><DashboardPage /></Suspended>,
          },
          {
            path: "onboarding",
            element: <Suspended><OnboardingPage /></Suspended>,
          },
          {
            path: "identifiers",
            element: <Suspended><IdentifiersPage /></Suspended>,
          },
          {
            path: "scans",
            element: <Suspended><ScansPage /></Suspended>,
          },
          {
            path: "scans/:scanId",
            element: <Suspended><ScanDetailPage /></Suspended>,
          },
          {
            path: "findings",
            element: <Suspended><FindingsPage /></Suspended>,
          },
          {
            path: "scores",
            element: <Suspended><ScoresPage /></Suspended>,
          },
          {
            path: "recommendations",
            element: <Suspended><RecommendationsPage /></Suspended>,
          },
          {
            path: "remediation",
            element: <Suspended><RemediationPage /></Suspended>,
          },
          {
            path: "identity",
            element: <Suspended><IdentityPage /></Suspended>,
          },
          {
            path: "privacy",
            element: <Suspended><PrivacyPage /></Suspended>,
          },
          {
            path: "timeline",
            element: <Suspended><TimelinePage /></Suspended>,
          },
          {
            path: "reviews",
            element: <Suspended><ReviewQueuePage /></Suspended>,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/app/onboarding" replace />,
  },
]);
