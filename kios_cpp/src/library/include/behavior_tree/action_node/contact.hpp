#include "behavior_tree/action_node/meta_node.hpp"

namespace Insertion

{
    class Contact : public MetaNode
    {
    public:
        Contact(const std::string &name, const BT::NodeConfig &config, std::shared_ptr<ActionNodeContext> context_ptr, std::shared_ptr<RobotState> state_ptr);

        static BT::PortsList providedPorts();

        BT::NodeStatus onStart() override;

        /// method invoked by an action in the RUNNING state.
        BT::NodeStatus onRunning() override;
        // Method invoked when interrupted
        void onHalted() override;

    private:
        int number;
        std::shared_ptr<ActionNodeContext> m_node_context_ptr;
        std::shared_ptr<RobotState> m_robot_state_ptr;
        void node_context_initialize();
        bool is_success();
        void set_action_context();
        std::chrono::system_clock::time_point deadline_;
    };

} // namespace Insertion
