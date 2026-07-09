import "react-native-url-polyfill/auto";
import { BlurView } from "expo-blur";
import { LinearGradient } from "expo-linear-gradient";
import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";
import { StatusBar } from "expo-status-bar";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import type { Session } from "@supabase/supabase-js";

import { callApi } from "./src/api";
import { supabase } from "./src/supabase";

WebBrowser.maybeCompleteAuthSession();

type Tab = "chat" | "tutor" | "actions" | "settings";
type ChatMessage = { role: "user" | "assistant"; content: string };
type ActionResult = {
  link: string;
  message: string;
  requires_user_confirmation: boolean;
};
type TutorResult = {
  topic: string;
  level: string;
  study_plan: string;
  resources: {
    title: string;
    url: string;
    resource_type: string;
    read_status: string;
    summary: string;
    why_useful: string;
  }[];
  steps: {
    order_index: number;
    title: string;
    goal: string;
    task: string;
  }[];
};

const quickPrompts = [
  "Design my own LM roadmap",
  "Explain transformer training",
  "Plan AI learning for Python",
  "Compare healthcare AI datasets",
];

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoadingSession(false);
    });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });

    return () => data.subscription.unsubscribe();
  }, []);

  return (
    <AppShell>
      <StatusBar style="light" />
      {loadingSession ? (
        <View style={styles.centered}>
          <ActivityIndicator color="#7cf7d4" />
          <Text style={styles.mutedText}>Starting ResearchMind</Text>
        </View>
      ) : session ? (
        <Home session={session} />
      ) : (
        <AuthScreen />
      )}
    </AppShell>
  );
}

function AuthScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function signInWithPassword(mode: "signin" | "signup") {
    setBusy(true);
    setError("");
    const result =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });
    setBusy(false);

    if (result.error) {
      setError(result.error.message);
    } else if (mode === "signup") {
      Alert.alert("Check email", "Confirm your account if email confirmation is enabled.");
    }
  }

  async function signInWithGoogle() {
    setError("");
    const redirectTo = Linking.createURL("auth/callback");
    const { data, error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo,
        skipBrowserRedirect: Platform.OS !== "web",
      },
    });

    if (authError) {
      setError(authError.message);
      return;
    }

    if (Platform.OS !== "web" && data.url) {
      const result = await WebBrowser.openAuthSessionAsync(data.url, redirectTo);
      if (result.type === "success") {
        const url = new URL(result.url);
        const code = url.searchParams.get("code");
        if (code) await supabase.auth.exchangeCodeForSession(code);
      }
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.auth} keyboardShouldPersistTaps="handled">
      <Glass style={styles.authCard}>
        <View style={styles.brandMark}>
          <Text style={styles.brandMarkText}>RM</Text>
        </View>
        <Text style={styles.logo}>ResearchMind</Text>
        <Text style={styles.heroText}>Build, test, and use your own learning model from one mobile lab.</Text>

        {error ? <StatusNote tone="bad" text={error} /> : <StatusNote tone="good" text="Private auth plus local LM-ready backend." />}

        <TextInput
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="Email"
          placeholderTextColor="#7f8d98"
          style={styles.input}
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          placeholder="Password"
          placeholderTextColor="#7f8d98"
          secureTextEntry
          style={styles.input}
          value={password}
          onChangeText={setPassword}
        />

        <Button label={busy ? "Working..." : "Sign In"} disabled={busy} onPress={() => signInWithPassword("signin")} />
        <View style={styles.authActions}>
          <Button label="Create Account" variant="secondary" disabled={busy} onPress={() => signInWithPassword("signup")} />
          <Button label="Google" variant="outline" onPress={signInWithGoogle} />
        </View>
      </Glass>
    </ScrollView>
  );
}

function Home({ session }: { session: Session }) {
  const [tab, setTab] = useState<Tab>("chat");
  const token = session.access_token;
  const email = session.user.email ?? "Account";

  return (
    <KeyboardAvoidingView style={styles.fill} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.title}>ResearchMind</Text>
            <Text style={styles.subtle}>{email}</Text>
          </View>
          <View style={styles.livePill}>
            <View style={styles.liveDot} />
            <Text style={styles.liveText}>LM Lab</Text>
          </View>
        </View>
        <Glass style={styles.statsRow}>
          <Metric label="Model" value="Prototype" />
          <Metric label="Backend" value="Local" />
          <Metric label="Mode" value={tab.toUpperCase()} />
        </Glass>
      </View>

      <View style={styles.tabs}>
        <TabButton active={tab === "chat"} label="Chat" onPress={() => setTab("chat")} />
        <TabButton active={tab === "tutor"} label="Tutor" onPress={() => setTab("tutor")} />
        <TabButton active={tab === "actions"} label="Actions" onPress={() => setTab("actions")} />
        <TabButton active={tab === "settings"} label="Settings" onPress={() => setTab("settings")} />
      </View>

      {tab === "chat" && <Chat token={token} />}
      {tab === "tutor" && <Tutor token={token} />}
      {tab === "actions" && <Actions token={token} />}
      {tab === "settings" && <Settings />}
    </KeyboardAvoidingView>
  );
}

function Chat({ token }: { token: string }) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "ResearchMind LM prototype is ready. Ask about your model, datasets, training, research plans, or app ideas.",
    },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<ScrollView>(null);

  async function send(textOverride?: string) {
    const text = (textOverride ?? message).trim();
    if (!text || busy) return;
    setMessage("");
    setError("");
    setMessages((current) => [...current, { role: "user", content: text }]);
    setBusy(true);

    try {
      const data = await callApi<{ reply: string }>("/ai/chat", token, { message: text });
      setMessages((current) => [...current, { role: "assistant", content: data.reply }]);
    } catch (caught) {
      const problem = caught instanceof Error ? caught.message : "Something went wrong.";
      setError(problem);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: `I could not reach the backend. Keep Metro and the FastAPI server running, then try again. Details: ${problem}`,
        },
      ]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => scrollRef.current?.scrollToEnd({ animated: true }));
    }
  }

  return (
    <View style={styles.panel}>
      {error ? <StatusNote tone="bad" text={error} /> : <StatusNote tone="good" text="Connected to your mobile AI lab." />}

      <ScrollView
        ref={scrollRef}
        style={styles.messages}
        contentContainerStyle={styles.messageContent}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.map((item, index) => (
          <MessageBubble key={`${item.role}-${index}`} message={item} />
        ))}
        {busy && (
          <Glass style={styles.thinkingBubble}>
            <ActivityIndicator color="#7cf7d4" />
            <Text style={styles.mutedText}>ResearchMind is thinking</Text>
          </Glass>
        )}
      </ScrollView>

      <View style={styles.promptRail}>
        {quickPrompts.map((prompt) => (
          <Chip key={prompt} label={prompt} onPress={() => send(prompt)} />
        ))}
      </View>

      <Glass style={styles.composerCard}>
        <TextInput
          multiline
          placeholder="Message your ResearchMind LM"
          placeholderTextColor="#7f8d98"
          style={styles.composerInput}
          value={message}
          onChangeText={setMessage}
        />
        <Button label={busy ? "Thinking" : "Send"} disabled={busy || !message.trim()} onPress={() => send()} />
      </Glass>
    </View>
  );
}

function Tutor({ token }: { token: string }) {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("beginner");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TutorResult | null>(null);

  async function researchTopic() {
    if (!topic.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await callApi<TutorResult>("/tutor/research", token, {
        topic: topic.trim(),
        level: level.trim() || "beginner",
      });
      setResult(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView style={styles.panel} contentContainerStyle={styles.scrollPanel} keyboardShouldPersistTaps="handled">
      <Glass style={styles.featureCard}>
        <Text style={styles.sectionTitle}>Learning Path Builder</Text>
        <Text style={styles.subtle}>Turn any topic into resources, steps, and practice work for your custom LM journey.</Text>
        {error ? <StatusNote tone="bad" text={error} /> : null}
        <TextInput
          placeholder="What do you want to learn?"
          placeholderTextColor="#7f8d98"
          style={styles.input}
          value={topic}
          onChangeText={setTopic}
        />
        <TextInput
          placeholder="Level"
          placeholderTextColor="#7f8d98"
          style={styles.input}
          value={level}
          onChangeText={setLevel}
        />
        <Button label={busy ? "Researching" : "Build Path"} disabled={busy || !topic.trim()} onPress={researchTopic} />
      </Glass>

      {result && (
        <View style={styles.resultStack}>
          <Glass style={styles.featureCard}>
            <Text style={styles.resultTitle}>{result.topic}</Text>
            <Text style={styles.bubbleText}>{result.study_plan}</Text>
          </Glass>

          <Text style={styles.sectionTitle}>Steps</Text>
          {result.steps.map((step) => (
            <Glass key={step.order_index} style={styles.resultCard}>
              <Text style={styles.bubbleLabel}>Step {step.order_index}</Text>
              <Text style={styles.resultTitle}>{step.title}</Text>
              <Text style={styles.bubbleText}>{step.goal}</Text>
              <Text style={styles.subtle}>{step.task}</Text>
            </Glass>
          ))}

          <Text style={styles.sectionTitle}>Resources</Text>
          {result.resources.map((resource) => (
            <Glass key={resource.url} style={styles.resultCard}>
              <Text style={styles.bubbleLabel}>
                {resource.resource_type} / {resource.read_status}
              </Text>
              <Text style={styles.resultTitle}>{resource.title}</Text>
              <Text style={styles.bubbleText}>{resource.summary}</Text>
              <Text style={styles.subtle}>{resource.why_useful}</Text>
              <Text style={styles.linkText}>{resource.url}</Text>
            </Glass>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function Actions({ token }: { token: string }) {
  const [command, setCommand] = useState("");
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ActionResult | null>(null);
  const examples = useMemo(
    () => ["open youtube.com", "search for AI internships", "call +919876543210", "WhatsApp +919876543210 saying I am on the way"],
    []
  );

  async function createAction() {
    if (!command.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const data = await callApi<ActionResult>("/voice-action", token, {
        command,
        phone_number: phone || null,
      });
      setResult(data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function openResult() {
    if (!result?.link) return;
    await Linking.openURL(result.link);
  }

  return (
    <ScrollView style={styles.panel} contentContainerStyle={styles.scrollPanel} keyboardShouldPersistTaps="handled">
      <Glass style={styles.featureCard}>
        <Text style={styles.sectionTitle}>Action Console</Text>
        <Text style={styles.subtle}>Prepare safe browser, phone, and WhatsApp actions with user confirmation.</Text>
        {error ? <StatusNote tone="bad" text={error} /> : null}
        <TextInput
          multiline
          placeholder="Type a command"
          placeholderTextColor="#7f8d98"
          style={[styles.input, styles.tallInput]}
          value={command}
          onChangeText={setCommand}
        />
        <TextInput
          keyboardType="phone-pad"
          placeholder="Optional phone number"
          placeholderTextColor="#7f8d98"
          style={styles.input}
          value={phone}
          onChangeText={setPhone}
        />
        <Button label={busy ? "Creating" : "Create Action"} disabled={busy || !command.trim()} onPress={createAction} />
      </Glass>

      <View style={styles.promptRail}>
        {examples.map((item) => (
          <Chip key={item} label={item} onPress={() => setCommand(item)} />
        ))}
      </View>

      {result && (
        <Glass style={styles.featureCard}>
          <Text style={styles.resultTitle}>{result.message}</Text>
          <Text style={styles.linkText}>{result.link}</Text>
          {result.requires_user_confirmation && <Text style={styles.warning}>Review before sending or calling.</Text>}
          <Button label="Open Action" onPress={openResult} />
        </Glass>
      )}
    </ScrollView>
  );
}

function Settings() {
  return (
    <ScrollView style={styles.panel} contentContainerStyle={styles.scrollPanel}>
      <Glass style={styles.featureCard}>
        <Text style={styles.sectionTitle}>ResearchMind Core</Text>
        <SettingRow label="Model path" value="Custom transformer in /model" />
        <SettingRow label="Backend" value="FastAPI on 10.0.2.2:8000" />
        <SettingRow label="Auth" value="Supabase session protected" />
        <SettingRow label="Actions" value="Confirmation-first links" />
        <Button label="Sign Out" variant="secondary" onPress={() => supabase.auth.signOut()} />
      </Glass>
    </ScrollView>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LinearGradient colors={["#06110f", "#101523", "#071819"]} style={styles.screen}>
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.glowOne} />
        <View style={styles.glowTwo} />
        {children}
      </SafeAreaView>
    </LinearGradient>
  );
}

function Glass({ children, style }: { children: React.ReactNode; style?: object }) {
  return (
    <BlurView intensity={30} tint="dark" style={[styles.glass, style]}>
      {children}
    </BlurView>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <View style={[styles.messageRow, isUser && styles.messageRowUser]}>
      <Glass style={[styles.messageBubble, isUser && styles.userMessageBubble]}>
        <Text style={styles.bubbleLabel}>{isUser ? "You" : "ResearchMind LM"}</Text>
        <Text style={styles.bubbleText}>{message.content}</Text>
      </Glass>
    </View>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.settingRow}>
      <Text style={styles.settingLabel}>{label}</Text>
      <Text style={styles.settingValue}>{value}</Text>
    </View>
  );
}

function StatusNote({ text, tone }: { text: string; tone: "good" | "bad" }) {
  return (
    <View style={[styles.statusNote, tone === "bad" && styles.statusBad]}>
      <View style={[styles.statusDot, tone === "bad" && styles.statusDotBad]} />
      <Text style={styles.statusText}>{text}</Text>
    </View>
  );
}

function Chip({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable style={styles.chip} onPress={onPress}>
      <Text style={styles.chipText}>{label}</Text>
    </Pressable>
  );
}

function Button({
  label,
  onPress,
  disabled,
  variant = "primary",
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "outline";
}) {
  const buttonStyle = {
    primary: styles.primaryButton,
    secondary: styles.secondaryButton,
    outline: styles.outlineButton,
  }[variant];
  const textStyle = variant === "primary" ? styles.primaryButtonText : styles.lightButtonText;

  return (
    <Pressable disabled={disabled} style={[styles.button, buttonStyle, disabled && styles.disabled]} onPress={onPress}>
      <Text style={[styles.buttonText, textStyle, variant === "outline" && styles.outlineButtonText]}>{label}</Text>
    </Pressable>
  );
}

function TabButton({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable style={[styles.tab, active && styles.activeTab]} onPress={onPress}>
      <Text style={[styles.tabText, active && styles.activeTabText]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    overflow: "hidden",
  },
  glowOne: {
    position: "absolute",
    top: -80,
    left: -80,
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: "rgba(30, 215, 166, 0.16)",
  },
  glowTwo: {
    position: "absolute",
    right: -90,
    bottom: 90,
    width: 260,
    height: 260,
    borderRadius: 130,
    backgroundColor: "rgba(96, 139, 255, 0.12)",
  },
  fill: {
    flex: 1,
  },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },
  auth: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 18,
  },
  authCard: {
    gap: 12,
    padding: 18,
    width: "100%",
    maxWidth: 560,
    alignSelf: "center",
  },
  authActions: {
    flexDirection: "row",
    gap: 10,
  },
  brandMark: {
    width: 54,
    height: 54,
    borderRadius: 16,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(124, 247, 212, 0.16)",
    borderWidth: 1,
    borderColor: "rgba(124, 247, 212, 0.36)",
  },
  brandMarkText: {
    color: "#7cf7d4",
    fontWeight: "900",
    fontSize: 18,
  },
  logo: {
    color: "#f6fffb",
    fontSize: 38,
    fontWeight: "900",
  },
  heroText: {
    color: "#b9c7d1",
    fontSize: 16,
    lineHeight: 23,
  },
  title: {
    color: "#f6fffb",
    fontSize: 29,
    fontWeight: "900",
  },
  subtle: {
    color: "#9ba8b4",
    fontSize: 14,
    lineHeight: 20,
  },
  mutedText: {
    color: "#93a2ad",
    fontSize: 13,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 10,
    gap: 12,
  },
  headerTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  livePill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingHorizontal: 11,
    minHeight: 34,
    borderRadius: 17,
    backgroundColor: "rgba(124, 247, 212, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(124, 247, 212, 0.34)",
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#7cf7d4",
  },
  liveText: {
    color: "#dffff4",
    fontWeight: "800",
    fontSize: 12,
  },
  glass: {
    borderRadius: 18,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.1)",
    backgroundColor: "rgba(10, 18, 24, 0.54)",
  },
  statsRow: {
    flexDirection: "row",
    paddingVertical: 12,
  },
  metric: {
    flex: 1,
    alignItems: "center",
    gap: 2,
  },
  metricValue: {
    color: "#f6fffb",
    fontWeight: "900",
    fontSize: 13,
  },
  metricLabel: {
    color: "#7f8d98",
    fontSize: 11,
    textTransform: "uppercase",
    fontWeight: "800",
  },
  tabs: {
    flexDirection: "row",
    gap: 8,
    padding: 12,
  },
  tab: {
    flex: 1,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.06)",
  },
  activeTab: {
    backgroundColor: "#7cf7d4",
    borderColor: "#7cf7d4",
  },
  tabText: {
    color: "#9ba8b4",
    fontWeight: "800",
    fontSize: 13,
  },
  activeTabText: {
    color: "#06110f",
  },
  panel: {
    flex: 1,
    paddingHorizontal: 14,
  },
  scrollPanel: {
    paddingBottom: 24,
    gap: 14,
  },
  messages: {
    flex: 1,
  },
  messageContent: {
    paddingBottom: 12,
    gap: 10,
  },
  messageRow: {
    flexDirection: "row",
    justifyContent: "flex-start",
  },
  messageRowUser: {
    justifyContent: "flex-end",
  },
  messageBubble: {
    maxWidth: "88%",
    padding: 13,
  },
  userMessageBubble: {
    backgroundColor: "rgba(33, 108, 83, 0.52)",
    borderColor: "rgba(124, 247, 212, 0.26)",
  },
  thinkingBubble: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    padding: 12,
    alignSelf: "flex-start",
  },
  promptRail: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    paddingVertical: 10,
  },
  chip: {
    minHeight: 34,
    justifyContent: "center",
    borderRadius: 17,
    paddingHorizontal: 12,
    backgroundColor: "rgba(255, 255, 255, 0.07)",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.1)",
  },
  chipText: {
    color: "#dce7ec",
    fontSize: 12,
    fontWeight: "700",
  },
  composerCard: {
    gap: 10,
    padding: 12,
    marginBottom: 12,
  },
  input: {
    minHeight: 50,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.12)",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: "rgba(3, 9, 13, 0.55)",
    color: "#f6fffb",
    fontSize: 15,
  },
  composerInput: {
    minHeight: 82,
    maxHeight: 140,
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#f6fffb",
    fontSize: 15,
    backgroundColor: "rgba(3, 9, 13, 0.5)",
    textAlignVertical: "top",
  },
  tallInput: {
    minHeight: 96,
    textAlignVertical: "top",
  },
  button: {
    minHeight: 48,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
  },
  primaryButton: {
    backgroundColor: "#7cf7d4",
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
  },
  outlineButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#7cf7d4",
    backgroundColor: "transparent",
  },
  disabled: {
    opacity: 0.55,
  },
  buttonText: {
    fontWeight: "900",
    fontSize: 15,
  },
  primaryButtonText: {
    color: "#06110f",
  },
  lightButtonText: {
    color: "#f6fffb",
  },
  outlineButtonText: {
    color: "#7cf7d4",
  },
  bubbleLabel: {
    color: "#7cf7d4",
    fontSize: 11,
    fontWeight: "900",
    marginBottom: 7,
    textTransform: "uppercase",
  },
  bubbleText: {
    color: "#edf8f5",
    lineHeight: 21,
    fontSize: 14,
  },
  sectionTitle: {
    color: "#f6fffb",
    fontSize: 22,
    fontWeight: "900",
  },
  featureCard: {
    gap: 12,
    padding: 15,
  },
  resultStack: {
    gap: 12,
  },
  resultCard: {
    gap: 8,
    padding: 13,
  },
  resultTitle: {
    color: "#f6fffb",
    fontWeight: "900",
    fontSize: 17,
  },
  linkText: {
    color: "#7cf7d4",
    lineHeight: 20,
  },
  warning: {
    color: "#ffd37a",
    fontWeight: "700",
  },
  statusNote: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    minHeight: 38,
    borderRadius: 12,
    paddingHorizontal: 11,
    backgroundColor: "rgba(124, 247, 212, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(124, 247, 212, 0.22)",
  },
  statusBad: {
    backgroundColor: "rgba(255, 90, 114, 0.12)",
    borderColor: "rgba(255, 90, 114, 0.3)",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#7cf7d4",
  },
  statusDotBad: {
    backgroundColor: "#ff6f85",
  },
  statusText: {
    flex: 1,
    color: "#dce7ec",
    fontSize: 12,
    lineHeight: 17,
    fontWeight: "700",
  },
  settingRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(255, 255, 255, 0.08)",
  },
  settingLabel: {
    color: "#7f8d98",
    fontWeight: "800",
    textTransform: "uppercase",
    fontSize: 11,
    marginBottom: 5,
  },
  settingValue: {
    color: "#f6fffb",
    fontSize: 15,
    fontWeight: "700",
  },
});
