import React, { useState } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    ActivityIndicator,
    Platform,
    KeyboardAvoidingView,
    ScrollView,
    TouchableWithoutFeedback,
    Keyboard
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authService } from '../services/authService';
import { colors, fonts, layout, lines, radius, spacing, typography } from '../ui/theme';

export default function AuthScreen({ onLogin }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [loading, setLoading] = useState(false);
    const [isSignUp, setIsSignUp] = useState(false);
    const [message, setMessage] = useState({ type: '', content: '' });

    async function handleAuth() {
        if (!email || !password) {
            setMessage({ type: 'error', content: 'Por favor, rellena todos los campos.' });
            return;
        }

        setLoading(true);
        setMessage({ type: '', content: '' });

        try {
            if (isSignUp) {
                if (!fullName) {
                    setMessage({ type: 'error', content: 'El nombre completo es obligatorio para el registro.' });
                    setLoading(false);
                    return;
                }
                await authService.signUp(email, password, fullName);
                setMessage({ type: 'success', content: '¡Registro casi listo! Revisa tu email para confirmar tu cuenta.' });
            } else {
                await authService.signIn(email, password);
                onLogin();
            }
        } catch (error) {
            setMessage({ type: 'error', content: error.message });
        } finally {
            setLoading(false);
        }
    }

    return (
        <SafeAreaView style={styles.container}>
            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={{ flex: 1 }}
                enabled={Platform.OS !== 'web'}
            >
                <View style={{ flex: 1 }}>

                    <ScrollView
                        contentContainerStyle={styles.scrollContent}
                        keyboardShouldPersistTaps="handled"
                    >
                        <View style={styles.logoContainer}>
                            <Text style={styles.title}>LetiSmartCoach</Text>
                            <Text style={styles.subtitle}>Mobile Phase 1</Text>
                        </View>

                        <View style={styles.form}>
                            {message.content ? (
                                <View style={[styles.messageBox, message.type === 'error' ? styles.errorBox : styles.successBox]}>
                                    <Text style={styles.messageText}>{message.content}</Text>
                                </View>
                            ) : null}

                            {isSignUp && (
                                <TextInput
                                    style={styles.input}
                                    placeholder="Nombre Completo"
                                    placeholderTextColor={colors.textDisabled}
                                    value={fullName}
                                    onChangeText={setFullName}
                                    autoCapitalize="words"
                                />
                            )}

                            <TextInput
                                style={styles.input}
                                placeholder="Email"
                                placeholderTextColor={colors.textDisabled}
                                value={email}
                                onChangeText={(text) => setEmail(text.trim())}
                                autoCapitalize="none"
                                keyboardType="email-address"
                            />
                            <TextInput
                                style={styles.input}
                                placeholder="Password"
                                placeholderTextColor={colors.textDisabled}
                                value={password}
                                onChangeText={setPassword}
                                secureTextEntry
                            />

                            <TouchableOpacity
                                style={[styles.button, loading && styles.buttonDisabled]}
                                onPress={handleAuth}
                                disabled={loading}
                            >
                                {loading ? (
                                    <ActivityIndicator color={colors.onPrimary} />
                                ) : (
                                    <Text style={styles.buttonText}>
                                        {isSignUp ? 'Crear Cuenta' : 'Entrar'}
                                    </Text>
                                )}
                            </TouchableOpacity>

                            <TouchableOpacity onPress={() => {
                                setIsSignUp(!isSignUp);
                                setMessage({ type: '', content: '' });
                            }}>
                                <Text style={styles.switchText}>
                                    {isSignUp ? '¿Ya tienes cuenta? Inicia sesión' : '¿No tienes cuenta? Regístrate'}
                                </Text>
                            </TouchableOpacity>
                        </View>
                    </ScrollView>
                </View>

            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: colors.background,
    },
    scrollContent: {
        flexGrow: 1,
        padding: spacing.xl,
        justifyContent: 'center',
        width: '100%',
        maxWidth: layout.formMaxWidth,
        alignSelf: 'center',
    },
    logoContainer: {
        marginBottom: spacing.xxxl,
        gap: spacing.xs,
    },
    title: {
        ...typography.display,
        color: colors.text,
    },
    subtitle: {
        ...typography.body,
        color: colors.textSecondary,
    },
    form: {
        gap: spacing.lg,
    },
    messageBox: {
        padding: spacing.md,
        borderRadius: radius.sm,
    },
    errorBox: {
        backgroundColor: colors.dangerSurface,
    },
    successBox: {
        backgroundColor: colors.surfaceSoft,
    },
    messageText: {
        ...typography.small,
        color: colors.text,
    },
    input: {
        ...typography.body,
        color: colors.text,
        borderWidth: lines.hairline,
        borderColor: colors.separatorStrong,
        borderRadius: radius.sm,
        paddingHorizontal: spacing.md,
        paddingVertical: spacing.md,
    },
    button: {
        backgroundColor: colors.primary,
        borderRadius: radius.sm,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 48,
        marginTop: spacing.sm,
    },
    buttonDisabled: {
        opacity: 0.45,
    },
    buttonText: {
        fontFamily: fonts.bold,
        fontSize: typography.body.fontSize,
        color: colors.onPrimary,
    },
    switchText: {
        ...typography.smallBold,
        color: colors.textActive,
        textAlign: 'center',
        marginTop: spacing.sm,
    },
});
