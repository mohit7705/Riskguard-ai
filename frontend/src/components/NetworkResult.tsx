import type { UserNetwork } from '../api/risk'

function NetworkResult({
  network,
}: {
  network: UserNetwork
}) {
  const targetUserCount = network.nodes.filter(
    (node) => node.type === 'USER' && !node.is_target,
  ).length

  const deviceCount = network.nodes.filter(
    (node) => node.type === 'DEVICE',
  ).length

  const addressCount = network.nodes.filter(
    (node) => node.type === 'ADDRESS',
  ).length

  const paymentCount = network.nodes.filter(
    (node) => node.type === 'PAYMENT',
  ).length

  return (
    <div className="network-result">
      <div className="network-overview">
        <div className="network-stat">
          <span>CONNECTED USERS</span>
          <strong>{targetUserCount}</strong>
        </div>

        <div className="network-stat">
          <span>SHARED DEVICES</span>
          <strong>{deviceCount}</strong>
        </div>

        <div className="network-stat">
          <span>SHARED ADDRESSES</span>
          <strong>{addressCount}</strong>
        </div>

        <div className="network-stat">
          <span>SHARED PAYMENTS</span>
          <strong>{paymentCount}</strong>
        </div>
      </div>

      <div className="network-summary">
        <h4>Network Risk Signals</h4>

        <div className="network-summary-grid">
          <div>
            <span>Device sharing</span>
            <strong>
              {network.network_summary.shared_device_count}
            </strong>
          </div>

          <div>
            <span>Address sharing</span>
            <strong>
              {network.network_summary.shared_address_count}
            </strong>
          </div>

          <div>
            <span>Payment sharing</span>
            <strong>
              {network.network_summary.shared_payment_fingerprint_count}
            </strong>
          </div>

          <div>
            <span>7d cluster returns</span>
            <strong>
              {network.network_summary.cluster_return_velocity_7d}
            </strong>
          </div>
        </div>
      </div>

      <div className="network-connections">
        <h4>Connected Accounts</h4>

        {network.nodes
          .filter(
            (node) =>
              node.type === 'USER' &&
              node.is_target === false,
          )
          .map((node) => (
            <div className="network-user" key={node.id}>
              <span>{node.label}</span>
              <small>CONNECTED ACCOUNT</small>
            </div>
          ))}

        {targetUserCount === 0 && (
          <p className="network-empty">
            No other connected accounts found.
          </p>
        )}
      </div>
    </div>
  )
}

export default NetworkResult
