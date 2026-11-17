import React, { useEffect, useState } from 'react';
import { Text } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { athleteApi } from '../../api/athleteApi';
import { errorText } from '../../api/errors';
import type { AvailabilityDay, PreferredTime, Sport, WeekAvailability } from '../../api/types';
import type { RootStackParamList } from '../../navigation/types';
import { Button, Card, Chips, Field, Loading, Screen, styles, SwitchField } from '../../ui/components';
import { numberToText, parseOptionalNumber } from '../../ui/forms';
import { options, PREFERRED_TIME_LABELS, SPORT_LABELS, WEEKDAY_LABELS } from '../../ui/labels';
import { useFocusLoad } from '../../ui/useAsync';

type Props = NativeStackScreenProps<RootStackParamList, 'Availability'>;

type DayForm = {
  weekday: number;
  is_preferred_rest: boolean;
  max_minutes: string;
  preferred_time: PreferredTime;
  sports: Sport[];
};

function toForm(week: WeekAvailability): DayForm[] {
  return [...week.days]
    .sort((a, b) => a.weekday - b.weekday)
    .map((d) => ({
      weekday: d.weekday,
      is_preferred_rest: d.is_preferred_rest ?? false,
      max_minutes: numberToText(d.max_minutes),
      preferred_time: d.preferred_time ?? 'any',
      sports: [...(d.sports ?? [])],
    }));
}

function toBody(days: DayForm[]): WeekAvailability | string {
  const out: AvailabilityDay[] = [];
  for (const d of days) {
    const minutes = parseOptionalNumber(d.max_minutes);
    if (minutes !== null && (Number.isNaN(minutes) || !Number.isInteger(minutes) || minutes < 0 || minutes > 1440)) {
      return `${WEEKDAY_LABELS[d.weekday]}: los minutos deben ser un entero entre 0 y 1440.`;
    }
    out.push({
      weekday: d.weekday,
      is_preferred_rest: d.is_preferred_rest,
      max_minutes: minutes,
      preferred_time: d.preferred_time,
      sports: d.sports,
    });
  }
  return { days: out };
}

export default function AvailabilityScreen({ navigation }: Props) {
  const { data, setData, loading, error, setError, reload } = useFocusLoad(athleteApi.getAvailability);
  const [days, setDays] = useState<DayForm[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setDays(toForm(data));
  }, [data]);

  const update = (weekday: number, patch: Partial<DayForm>) => {
    setSaved(false);
    setDays((ds) => ds?.map((d) => (d.weekday === weekday ? { ...d, ...patch } : d)) ?? ds);
  };

  const save = async () => {
    if (!days) return;
    const body = toBody(days);
    if (typeof body === 'string') return setError(body);
    setSaving(true);
    setError(null);
    try {
      setData(await athleteApi.replaceAvailability(body));
      setSaved(true);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Screen error={error} onDismissError={() => setError(null)} title="Disponibilidad semanal" onBack={navigation.goBack} refreshing={loading && !!data} onRefresh={reload}>
      {loading && !days ? <Loading /> : null}
      {days ? (
        <>
          <Text style={styles.muted}>Tiempo habitual que tienes para entrenar cada día. Deja los minutos vacíos si no hay límite.</Text>
          {days.map((d) => (
            <Card key={d.weekday} title={WEEKDAY_LABELS[d.weekday]}>
              <SwitchField label="Descanso preferido" value={d.is_preferred_rest} onValueChange={(v) => update(d.weekday, { is_preferred_rest: v })} />
              <Field
                label="Minutos disponibles"
                value={d.max_minutes}
                onChangeText={(v) => update(d.weekday, { max_minutes: v })}
                keyboardType="number-pad"
                placeholder="Sin límite"
              />
              <Chips
                label="Momento preferido"
                options={options(PREFERRED_TIME_LABELS)}
                value={d.preferred_time}
                onChange={(v) => update(d.weekday, { preferred_time: v })}
              />
              <Chips label="Deportes" options={options(SPORT_LABELS)} value={d.sports} onChange={(v) => update(d.weekday, { sports: v })} multiple />
            </Card>
          ))}
          <Button title={saved ? 'Guardado' : 'Guardar semana'} onPress={save} loading={saving} />
        </>
      ) : null}
    </Screen>
  );
}
