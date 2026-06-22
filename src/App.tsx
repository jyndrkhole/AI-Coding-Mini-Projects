import { useEffect, useMemo, useRef, useState } from 'react'
import { SpeechRecognition as NativeSpeechRecognition } from '@capacitor-community/speech-recognition'
import { TextToSpeech, type SpeechSynthesisVoice as NativeTtsVoice } from '@capacitor-community/text-to-speech'
import { Capacitor } from '@capacitor/core'
import './App.css'

type WeekDay =
  | 'monday'
  | 'tuesday'
  | 'wednesday'
  | 'thursday'
  | 'friday'
  | 'saturday'
  | 'sunday'

type Timetable = Record<WeekDay, string[]>

type SpeechRecognitionConstructor = new () => BrowserSpeechRecognition

interface BrowserSpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  onend: (() => void) | null
  onerror: ((event: BrowserSpeechRecognitionErrorEvent) => void) | null
  onresult: ((event: BrowserSpeechRecognitionEvent) => void) | null
  abort: () => void
  start: () => void
  stop: () => void
}

interface BrowserSpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}

interface BrowserSpeechRecognitionErrorEvent extends Event {
  error: string
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

const weekDays: WeekDay[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
]

const dayLabels: Record<WeekDay, string> = {
  monday: 'Monday',
  tuesday: 'Tuesday',
  wednesday: 'Wednesday',
  thursday: 'Thursday',
  friday: 'Friday',
  saturday: 'Saturday',
  sunday: 'Sunday',
}

const sampleTimetable: Timetable = {
  monday: ['Moral Science', 'English', 'English', 'Mathematics', 'Marathi', 'Grammar', 'Environmental Science', 'Drawing', 'PT'],
  tuesday: ['Moral Science', 'English', 'Mathematics', 'Mathematics', 'Environmental Science', 'English', 'Grammar', 'Craft', 'Games'],
  wednesday: ['Moral Science', 'Mathematics', 'English', 'Marathi', 'Grammar', 'Environmental Science', 'Environmental Science', 'Drawing', 'PT'],
  thursday: ['Mathematics', 'English', 'Grammar', 'Composition', 'Mathematics', 'Library', 'Environmental Science', 'Environmental Science', 'Reading'],
  friday: ['Moral Science', 'Mathematics', 'Marathi', 'English', 'Grammar', 'Reading', 'Environmental Science', 'Craft', 'General Knowledge'],
  saturday: ['MPT/ Yoga', 'Singing', 'Dictation', 'Mathematics', 'Games'],
  sunday: [],
}

const storageKey = 'buddy-school-timetable'
const intervalStorageKey = 'buddy-read-interval'
const wakePhrase = 'hey buddy'
const indianEnglishLang = 'en-IN'
const femaleVoiceHints = [
  'female',
  'woman',
  'girl',
  'veena',
  'heera',
  'lekha',
  'neha',
  'rani',
  'priya',
  'aisha',
  'shruti',
  'swara',
  'samantha',
  'karen',
  'moira',
  'tessa',
  'fiona',
  'victoria',
  'zira',
  'susan',
  'kate',
  'serena',
  'allison',
  'ava',
  'sara',
  'nicky',
]
const maleVoiceHints = [
  'male',
  'man',
  'boy',
  'rishi',
  'ravi',
  'daniel',
  'david',
  'james',
  'tom',
  'fred',
  'alex',
  'aaron',
  'nathan',
  'oliver',
]

function getToday(): WeekDay {
  const dayIndex = new Date().getDay()
  return weekDays[(dayIndex + 6) % 7]
}

function normalizeSubjects(value: string) {
  return value
    .split('\n')
    .map((subject) => subject.trim())
    .filter(Boolean)
}

function getSpeechRecognition() {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition
}

function isMaleVoice(voice: Pick<SpeechSynthesisVoice | NativeTtsVoice, 'name'>) {
  const name = voice.name.toLowerCase()
  return maleVoiceHints.some((hint) => name.includes(hint))
}

function isFemaleVoice(voice: Pick<SpeechSynthesisVoice | NativeTtsVoice, 'name'>) {
  const name = voice.name.toLowerCase()
  return femaleVoiceHints.some((hint) => name.includes(hint))
}

function getVoiceScore(voice: Pick<SpeechSynthesisVoice | NativeTtsVoice, 'lang' | 'name'>) {
  const name = voice.name.toLowerCase()
  const lang = voice.lang.toLowerCase()
  let score = 0

  if (isMaleVoice(voice)) {
    return -1000
  }

  if (isFemaleVoice(voice)) {
    score += 200
  }

  if (lang === indianEnglishLang.toLowerCase()) {
    score += 100
  } else if (lang.startsWith('en-')) {
    score += 40
  }

  if (name.includes('india') || name.includes('indian')) {
    score += 30
  }

  return score
}

function getPreferredVoice<T extends Pick<SpeechSynthesisVoice | NativeTtsVoice, 'lang' | 'name'>>(
  voices: T[],
) {
  const ranked = voices
    .map((voice, index) => ({ voice, index, score: getVoiceScore(voice) }))
    .filter((entry) => entry.score > 0)
    .sort((first, second) => second.score - first.score)

  if (ranked.length > 0) {
    return ranked[0]
  }

  const femaleOnly = voices
    .map((voice, index) => ({ voice, index }))
    .filter((entry) => isFemaleVoice(entry.voice))

  if (femaleOnly.length > 0) {
    return femaleOnly[0]
  }

  const nonMale = voices
    .map((voice, index) => ({ voice, index }))
    .filter((entry) => !isMaleVoice(entry.voice))

  return nonMale[0]
}

function App() {
  const [selectedDay, setSelectedDay] = useState<WeekDay>(getToday)
  const [timetable, setTimetable] = useState<Timetable>(() => {
    const saved = localStorage.getItem(storageKey)

    if (!saved) {
      return sampleTimetable
    }

    try {
      return { ...sampleTimetable, ...JSON.parse(saved) } as Timetable
    } catch {
      return sampleTimetable
    }
  })
  const [intervalSeconds, setIntervalSeconds] = useState(() => {
    const saved = Number(localStorage.getItem(intervalStorageKey))
    return Number.isFinite(saved) && saved > 0 ? saved : 10
  })
  const [isPacking, setIsPacking] = useState(false)
  const [currentIndex, setCurrentIndex] = useState<number | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [lastCommand, setLastCommand] = useState('Say "Hey buddy, pack my bag" after tapping Listen.')
  const [status, setStatus] = useState('Ready to help pack the school bag.')
  const [browserVoices, setBrowserVoices] = useState<SpeechSynthesisVoice[]>([])
  const [voiceStatus, setVoiceStatus] = useState(() =>
    'speechSynthesis' in window ? 'Loading available voices...' : 'Speech output is not available in this browser.',
  )
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null)
  const sessionRef = useRef(0)
  const timeoutRef = useRef<number | null>(null)
  const nativeVoiceIndexRef = useRef<number | null | undefined>(undefined)

  const subjects = timetable[selectedDay]
  const subjectText = useMemo(() => subjects.join('\n'), [subjects])

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(timetable))
  }, [timetable])

  useEffect(() => {
    localStorage.setItem(intervalStorageKey, String(intervalSeconds))
  }, [intervalSeconds])

  useEffect(() => {
    if (Capacitor.isNativePlatform()) {
      void getNativeVoiceIndex()
      return
    }

    if (!('speechSynthesis' in window)) {
      return
    }

    const refreshVoices = () => {
      const voices = window.speechSynthesis.getVoices()
      setBrowserVoices(voices)

      const preferredVoice = getPreferredVoice(voices)

      if (preferredVoice) {
        setVoiceStatus(`${preferredVoice.voice.name} (${preferredVoice.voice.lang})`)
      } else {
        setVoiceStatus('Using browser default voice.')
      }
    }

    window.setTimeout(refreshVoices, 0)
    window.speechSynthesis.addEventListener('voiceschanged', refreshVoices)

    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', refreshVoices)
    }
  }, [])

  useEffect(() => {
    return () => {
      stopPacking()
      recognitionRef.current?.abort()
    }
  }, [])

  function updateSubjects(value: string) {
    setTimetable((current) => ({
      ...current,
      [selectedDay]: normalizeSubjects(value),
    }))
  }

  async function getNativeVoiceIndex() {
    if (nativeVoiceIndexRef.current !== undefined) {
      return nativeVoiceIndexRef.current
    }

    try {
      const { voices } = await TextToSpeech.getSupportedVoices()
      const preferredVoice = getPreferredVoice(voices)
      nativeVoiceIndexRef.current = preferredVoice?.index ?? null
      setVoiceStatus(
        preferredVoice
          ? `${preferredVoice.voice.name} (${preferredVoice.voice.lang})`
          : 'Using Android default voice.',
      )
    } catch {
      nativeVoiceIndexRef.current = null
      setVoiceStatus('Using Android default voice.')
    }

    return nativeVoiceIndexRef.current
  }

  function getBrowserVoice() {
    if (!('speechSynthesis' in window)) {
      return undefined
    }

    const voices = window.speechSynthesis.getVoices()
    return getPreferredVoice(browserVoices.length > 0 ? browserVoices : voices)?.voice
  }

  async function speak(message: string) {
    if (Capacitor.isNativePlatform()) {
      const voice = await getNativeVoiceIndex()

      return TextToSpeech.speak({
        text: message,
        lang: indianEnglishLang,
        rate: 0.86,
        pitch: 1.08,
        volume: 1,
        ...(voice !== null ? { voice } : {}),
      }).catch(() => undefined)
    }

    return new Promise<void>((resolve) => {
      if (!('speechSynthesis' in window)) {
        resolve()
        return
      }

      const utterance = new SpeechSynthesisUtterance(message)
      const preferredVoice = getBrowserVoice()
      utterance.lang = preferredVoice?.lang ?? indianEnglishLang
      utterance.voice = preferredVoice ?? null
      utterance.rate = 0.86
      utterance.pitch = 1.08
      utterance.onend = () => resolve()
      utterance.onerror = () => resolve()
      window.speechSynthesis.speak(utterance)
    })
  }

  function wait(milliseconds: number) {
    return new Promise<void>((resolve) => {
      timeoutRef.current = window.setTimeout(() => {
        timeoutRef.current = null
        resolve()
      }, milliseconds)
    })
  }

  function stopPacking() {
    sessionRef.current += 1
    setIsPacking(false)
    setCurrentIndex(null)

    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }

    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }

    if (Capacitor.isNativePlatform()) {
      void TextToSpeech.stop()
    }
  }

  async function startPacking(day: WeekDay = selectedDay) {
    stopPacking()

    const session = sessionRef.current
    const daySubjects = timetable[day]

    setSelectedDay(day)
    setIsPacking(true)
    setStatus(`Reading ${dayLabels[day]}'s subjects.`)

    if (daySubjects.length === 0) {
      await speak(`No subjects saved for ${dayLabels[day]}.`)
      setIsPacking(false)
      setStatus(`No subjects saved for ${dayLabels[day]}.`)
      return
    }

    for (const [index, subject] of daySubjects.entries()) {
      if (session !== sessionRef.current) {
        return
      }

      setCurrentIndex(index)
      setStatus(`Pack ${subject}`)
      await speak(subject)

      if (index < daySubjects.length - 1) {
        await wait(intervalSeconds * 1000)
      }
    }

    if (session === sessionRef.current) {
      setCurrentIndex(null)
      setIsPacking(false)
      setStatus('Bag packing list completed.')
      await speak('Done. Your school bag list is complete.')
    }
  }

  function handleCommand(command: string) {
    const normalized = command.toLowerCase()
    setLastCommand(command)

    if (!normalized.includes(wakePhrase)) {
      setStatus(`I heard "${command}", but I am waiting for "Hey buddy".`)
      return
    }

    if (normalized.includes('stop')) {
      stopPacking()
      setStatus('Stopped the packing list.')
      return
    }

    const requestedDay = weekDays.find((day) => normalized.includes(day))
    void startPacking(requestedDay ?? getToday())
  }

  async function startListening() {
    if (Capacitor.isNativePlatform()) {
      setIsListening(true)
      setStatus(`Listening for "${wakePhrase}"...`)

      try {
        const availability = await NativeSpeechRecognition.available()

        if (!availability.available) {
          setStatus('Speech recognition is not available on this Android device.')
          return
        }

        const permission = await NativeSpeechRecognition.requestPermissions()

        if (permission.speechRecognition !== 'granted') {
          setStatus('Microphone permission is required for voice commands.')
          return
        }

        const result = await NativeSpeechRecognition.start({
          language: 'en-IN',
          maxResults: 3,
          prompt: 'Say "Hey buddy, pack my bag"',
          popup: true,
          partialResults: false,
        })

        const command = result.matches?.[0]?.trim()

        if (command) {
          handleCommand(command)
        } else {
          setStatus('I did not hear a command. Please try again.')
        }
      } catch {
        setStatus('Voice recognition could not start. Please try again.')
      } finally {
        setIsListening(false)
      }

      return
    }

    const Recognition = getSpeechRecognition()

    if (!Recognition) {
      setStatus('Voice recognition is not available in this browser. Try Chrome or the Android app.')
      return
    }

    const recognition = new Recognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-IN'

    recognition.onresult = (event) => {
      const command = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()

      if (command) {
        handleCommand(command)
      }
    }

    recognition.onerror = (event) => {
      setStatus(`Voice recognition error: ${event.error}`)
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognitionRef.current = recognition
    setIsListening(true)
    setStatus(`Listening for "${wakePhrase}"...`)
    recognition.start()
  }

  return (
    <main className="app-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Voice timetable assistant</p>
          <h1>Hey Buddy Bag Packer</h1>
          <p className="hero-copy">
            Save the school timetable locally, then let the app read today&apos;s subjects
            one by one while you pack the bag steadily.
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" className="primary-button" onClick={() => void startPacking()}>
            Start today
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => void startListening()}
            disabled={isListening}
          >
            {isListening ? 'Listening...' : 'Listen'}
          </button>
        </div>
      </section>

      <section className="status-card" aria-live="polite">
        <div>
          <span className="status-label">Status</span>
          <p>{status}</p>
        </div>
        <div>
          <span className="status-label">Last voice command</span>
          <p>{lastCommand}</p>
        </div>
        <div>
          <span className="status-label">Selected voice</span>
          <p>{voiceStatus}</p>
        </div>
      </section>

      <section className="content-grid">
        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Timetable</p>
              <h2>Edit subjects</h2>
            </div>
            <label className="interval-control">
              Gap
              <input
                type="number"
                min="2"
                max="60"
                value={intervalSeconds}
                onChange={(event) => setIntervalSeconds(Number(event.target.value))}
              />
              sec
            </label>
          </div>

          <div className="day-tabs" role="tablist" aria-label="Timetable days">
            {weekDays.map((day) => (
              <button
                type="button"
                role="tab"
                aria-selected={selectedDay === day}
                className={selectedDay === day ? 'active' : ''}
                key={day}
                onClick={() => setSelectedDay(day)}
              >
                {dayLabels[day].slice(0, 3)}
              </button>
            ))}
          </div>

          <label className="subject-editor">
            Subjects for {dayLabels[selectedDay]}
            <textarea
              value={subjectText}
              onChange={(event) => updateSubjects(event.target.value)}
              rows={8}
              placeholder="Enter one subject per line"
            />
          </label>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Packing sequence</p>
              <h2>{dayLabels[selectedDay]}</h2>
            </div>
            {isPacking ? (
              <button type="button" className="secondary-button danger" onClick={stopPacking}>
                Stop
              </button>
            ) : (
              <button type="button" className="secondary-button" onClick={() => void startPacking()}>
                Read list
              </button>
            )}
          </div>

          {subjects.length > 0 ? (
            <ol className="subject-list">
              {subjects.map((subject, index) => (
                <li className={currentIndex === index ? 'current' : ''} key={`${subject}-${index}`}>
                  <span>{subject}</span>
                  {currentIndex === index && <strong>Pack now</strong>}
                </li>
              ))}
            </ol>
          ) : (
            <p className="empty-state">
              No subjects saved for this day. Add subjects on the left, one per line.
            </p>
          )}

          <div className="voice-help">
            <div className="voice-help-heading">
              <h3>Voice commands</h3>
              <button
                type="button"
                className="voice-test-button"
                onClick={() => void speak('Hello buddy. Let us pack your school bag together.')}
              >
                Test voice
              </button>
            </div>
            <p>Tap Listen, then say: &quot;Hey buddy, pack my bag&quot;.</p>
            <p>For a specific day: &quot;Hey buddy, Monday timetable&quot;.</p>
            <p>To stop: &quot;Hey buddy, stop&quot;.</p>
            <p>The app prefers an Indian English female voice when your device provides one.</p>
          </div>
        </div>
      </section>
    </main>
  )
}

export default App
