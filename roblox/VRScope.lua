-- Optical pose only: the native renderer supplies the magnified lens image.
local M={}
local G=require(game.ReplicatedStorage:WaitForChild('HexagonVRWeaponGeometry'))
function M.new(player,box,weapons)
    local self={}
    function self:clear(sequence)box.scope_state.Value=Vector3.new(sequence or 0,0,87003.5)end
    function self:update(sequence,blocked,native)
        self:clear(sequence);if blocked or not native then return end
        local folder=workspace:FindFirstChild('HexagonVRWeapons');if not folder then return end
        local eye=workspace.CurrentCamera.CoordinateFrame
        for _,model in ipairs(folder:GetChildren())do
            local owner=model:FindFirstChild('Owner');local layout=G.forModel(model)
            if owner and owner.Value==player and layout and layout.ScopeFrame then
                local hand=model:FindFirstChild('Hand');local held=hand and weapons.heldFrames[hand.Value]
                if not held or held.model~=model then return end
                local root=weapons:visualRoot(model)
                local lens=root.CFrame*layout.ScopeFrame;local relative=lens:pointToObjectSpace(eye.p)
                local radius=layout.ScopeRadius
                if relative.z>.15 and relative.z<1.1 and Vector3.new(relative.x,relative.y,0).magnitude<radius+.11 and eye.lookVector:Dot(lens.lookVector)>.965 then
                    local objective=(lens*CFrame.new(0,0,-layout.ScopeLength)).p
                    local hit=workspace:FindPartOnRayWithIgnoreList(Ray.new(eye.p,objective-eye.p),{folder,player.Character,workspace.CurrentCamera},false,true)
                    if not hit then
                        box.scope_frame.Value=lens
                        box.scope_params.Value=Vector3.new(radius,layout.ScopeZoom,layout.ScopeLength)
                        box.scope_state.Value=Vector3.new(sequence,1,87003.5)
                    end
                end
                return
            end
        end
    end
    return self
end
return M
