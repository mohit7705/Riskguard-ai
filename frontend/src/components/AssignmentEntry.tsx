import { useState } from 'react'
import {
  getAssignment,
  createAssignment,
  type Assignment,
} from '../api/assignment'

type AssignmentEntryProps = {
  onAssignmentSelected: (assignment: Assignment) => void
}

function AssignmentEntry({
  onAssignmentSelected,
}: AssignmentEntryProps) {
  const [emailInput, setEmailInput] = useState('')
  const [assignmentNumberInput, setAssignmentNumberInput] = useState('')
  const [assignmentNameInput, setAssignmentNameInput] = useState('')

  const [entryStep, setEntryStep] = useState<
    'email' | 'assignment'
  >('email')

  const [assignmentMode, setAssignmentMode] = useState<
    'lookup' | 'create'
  >('lookup')

  const [entryLoading, setEntryLoading] = useState(false)
  const [entryError, setEntryError] = useState('')

  const handleEmailContinue = async () => {
    const value = emailInput.trim()

    if (!value) {
      setEntryError(
        'Please enter your email or assignment number.',
      )
      return
    }

    const isEmail = /^\S+@\S+\.\S+$/.test(value)
    const isNumber = /^\d+$/.test(value)

    if (!isEmail && !isNumber) {
      setEntryError(
        'Enter a valid Gmail/email or assignment number.',
      )
      return
    }

    setEntryError('')

    if (isNumber) {
      setAssignmentNumberInput(value)
      setEntryLoading(true)

      try {
        const existing = await getAssignment(value)

        if (existing) {
          onAssignmentSelected(existing)
        } else {
          setAssignmentMode('create')
          setEntryStep('assignment')
        }
      } catch (err) {
        setEntryError(
          err instanceof Error
            ? err.message
            : 'Unable to check assignment.',
        )
      } finally {
        setEntryLoading(false)
      }

      return
    }

    setEntryStep('assignment')
  }

  const handleAssignmentLookup = async () => {
    const number = assignmentNumberInput.trim()

    if (!number) {
      setEntryError('Please enter an assignment number.')
      return
    }

    setEntryLoading(true)
    setEntryError('')

    try {
      const existing = await getAssignment(number)

      if (existing) {
        onAssignmentSelected(existing)
      } else {
        setAssignmentMode('create')
        setEntryError('')
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to find assignment.'

      setEntryError(message)
    } finally {
      setEntryLoading(false)
    }
  }

  const handleAssignmentCreate = async () => {
    const number = assignmentNumberInput.trim()
    const name = assignmentNameInput.trim()

    if (!number) {
      setEntryError('Please enter an assignment number.')
      return
    }

    if (!name) {
      setEntryError('Please enter an assignment name.')
      return
    }

    setEntryLoading(true)
    setEntryError('')

    try {
      const created = await createAssignment(number, name)

      onAssignmentSelected(created)
    } catch (err) {
      setEntryError(
        err instanceof Error
          ? err.message
          : 'Unable to create assignment.',
      )
    } finally {
      setEntryLoading(false)
    }
  }

  return (
    <div className="entry-shell">
      <div className="entry-card">
        <div className="entry-brand">
          <div className="brand-mark">R</div>

          <div>
            <h1>RiskGuard AI</h1>
            <span>Return Abuse Intelligence</span>
          </div>
        </div>

        {entryStep === 'email' && (
          <>
            <div className="entry-heading">
              <p className="eyebrow">WELCOME</p>

              <h2>Welcome to RiskGuard AI</h2>

              <p>
                Enter your email or assignment number to
                continue to your risk intelligence workspace.
              </p>
            </div>

            <div className="entry-form">
              <label htmlFor="email">
                Email or assignment number
              </label>

              <input
                id="email"
                type="text"
                value={emailInput}
                onChange={(event) => {
                  setEmailInput(event.target.value)
                  setEntryError('')
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleEmailContinue()
                  }
                }}
                placeholder="you@example.com or 98765"
                autoFocus
              />

              {entryError && (
                <div className="entry-error">
                  {entryError}
                </div>
              )}

              <button
                type="button"
                onClick={handleEmailContinue}
                disabled={entryLoading}
              >
                {entryLoading ? 'Checking...' : 'Continue'}
              </button>
            </div>
          </>
        )}

        {entryStep === 'assignment' && (
          <>
            <div className="entry-heading">
              <p className="eyebrow">WORKSPACE</p>

              <h2>Open your assignment</h2>

              <p>
                Enter the assignment number to open an existing
                workspace or create a new one.
              </p>
            </div>

            <div className="entry-form">
              <label htmlFor="assignment-number">
                Assignment number
              </label>

              <input
                id="assignment-number"
                type="text"
                value={assignmentNumberInput}
                onChange={(event) => {
                  setAssignmentNumberInput(event.target.value)
                  setEntryError('')
                  setAssignmentMode('lookup')
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    handleAssignmentLookup()
                  }
                }}
                placeholder="e.g. 98765"
                autoFocus
              />

              {assignmentMode === 'create' && (
                <>
                  <label htmlFor="assignment-name">
                    Assignment name
                  </label>

                  <input
                    id="assignment-name"
                    type="text"
                    value={assignmentNameInput}
                    onChange={(event) => {
                      setAssignmentNameInput(event.target.value)
                      setEntryError('')
                    }}
                    placeholder="e.g. Return Abuse Analysis"
                  />
                </>
              )}

              {entryError && (
                <div className="entry-error">
                  {entryError}
                </div>
              )}

              {assignmentMode === 'lookup' ? (
                <button
                  type="button"
                  onClick={handleAssignmentLookup}
                  disabled={entryLoading}
                >
                  {entryLoading
                    ? 'Checking...'
                    : 'Open Assignment'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleAssignmentCreate}
                  disabled={entryLoading}
                >
                  {entryLoading
                    ? 'Creating...'
                    : 'Create Assignment'}
                </button>
              )}

              <button
                type="button"
                className="entry-secondary"
                onClick={() => {
                  setEntryStep('email')
                  setEntryError('')
                }}
              >
                Back
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default AssignmentEntry
