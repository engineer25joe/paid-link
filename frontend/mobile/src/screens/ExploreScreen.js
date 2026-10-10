import { useEffect, useState } from 'react';
import { ActivityIndicator, Text, View } from 'react-native';
import { api } from '../api/client';
import { API_PATHS } from '../api/config';
import { getApiErrorMessage } from '../api/errors';
import { AppButton } from '../components/AppButton';
import { PageHeading, Screen } from '../components/Screen';

export function ExploreScreen({ navigation }) {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState({ loading: true, error: '' });
  useEffect(() => {
    let active = true;
    api.get(API_PATHS.content, { authenticated: false }).then((result) => {
      if (active) { setItems(Array.isArray(result) ? result : []); setStatus({ loading: false, error: '' }); }
    }).catch((error) => {
      if (active) setStatus({ loading: false, error: getApiErrorMessage(error.data, error.message) });
    });
    return () => { active = false; };
  }, []);
  return <Screen><View style={{ flex: 1, paddingVertical: 22 }}><PageHeading eyebrow="Explore" title="Learning resources" description="Browse published resources shared by creators."/>
    {status.loading && <ActivityIndicator accessibilityLabel="Loading resources"/>}
    {status.error ? <Text accessibilityRole="alert">Could not load resources: {status.error}</Text> : null}
    {!status.loading && !status.error && items.length === 0 ? <Text>No resources have been published yet.</Text> : null}
    {items.map((item) => <View key={item.id} style={{ backgroundColor: '#fff', borderColor: '#e1e7e2', borderWidth: 1, padding: 16, marginVertical: 7 }}><Text style={{ color: '#667274', textTransform: 'uppercase', fontSize: 11 }}>{item.content_type} · {item.creator_username}</Text><Text style={{ color: '#182326', fontSize: 19, fontWeight: '600', marginVertical: 7 }}>{item.title}</Text><Text style={{ color: '#667274', lineHeight: 21 }}>{item.description}</Text><Text style={{ color: '#182326', marginTop: 12 }}>{item.price} credits</Text></View>)}
    <View style={{ marginTop: 16 }}><AppButton title="Back to workspace" secondary onPress={() => navigation.goBack()}/></View>
  </View></Screen>;
}
